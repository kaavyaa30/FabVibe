"""
Import real product images from a manifest file or a folder into the database.

Usage
─────
# From the manifest file (admin_panel/upload_image.md):
    python manage.py import_images

# From a specific manifest file:
    python manage.py import_images --manifest path/to/upload_image.md

# From a folder — every image is matched to a product by filename stem:
    python manage.py import_images --folder path/to/images/

# Dry-run (shows what would happen, changes nothing):
    python manage.py import_images --dry-run

Manifest format (upload_image.md)
──────────────────────────────────
Each non-blank, non-comment line must be:

    product name - /absolute/or/relative/path/to/image.jpg

The product name is matched case-insensitively against Product.name.
Multiple lines for the same product add multiple images; the first one
becomes primary if the product has no images yet.

Folder mode
───────────
File names are used as the product name hint.  The stem is cleaned
(hyphens/underscores → spaces, trailing -0 / -1 suffixes stripped) and
matched against Product.name.  Example:
    black-casual-t-shirt-0.jpg  →  "black casual t shirt"  →  Black Casual T-Shirt
"""
import os
import re
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from products.models import Product, ProductImage

# Supported image extensions
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

# Default manifest path relative to BASE_DIR
DEFAULT_MANIFEST = 'admin_panel/upload_image.md'


def _clean_stem(stem: str) -> str:
    """Turn a filename stem into a searchable product name."""
    # Remove trailing index suffix like -0, -1, _0, _1
    stem = re.sub(r'[-_]\d+$', '', stem)
    # Replace hyphens/underscores with spaces
    stem = stem.replace('-', ' ').replace('_', ' ')
    return stem.strip().lower()


def _find_product(name_hint: str):
    """
    Find a Product by name hint.
    1. Exact case-insensitive match.
    2. Product name contains the hint.
    3. Hint contains the product name.
    Returns the first match or None.
    """
    qs = Product.objects.filter(name__iexact=name_hint)
    if qs.exists():
        return qs.first()
    qs = Product.objects.filter(name__icontains=name_hint)
    if qs.exists():
        return qs.first()
    qs = Product.objects.filter(name__icontains=name_hint.split()[0]) if name_hint.split() else Product.objects.none()
    if qs.exists():
        return qs.first()
    return None


def _dest_filename(product: Product, src_path: Path) -> str:
    """Build a unique destination filename inside media/products/."""
    stem = slugify(product.name)
    existing = ProductImage.objects.filter(product=product).count()
    return f"{stem}-{existing}{src_path.suffix.lower()}"


def _import_image(product: Product, src_path: Path, dry_run: bool, stdout, style):
    """Copy src_path into media/products/ and create a ProductImage record."""
    if not src_path.exists():
        stdout.write(style.WARNING(f"  ✗ File not found: {src_path}"))
        return False

    dest_filename = _dest_filename(product, src_path)
    dest_dir  = Path(settings.MEDIA_ROOT) / 'products'
    dest_path = dest_dir / dest_filename
    relative  = f"products/{dest_filename}"

    # Check for duplicate (same relative path already in DB)
    if ProductImage.objects.filter(product=product, image=relative).exists():
        stdout.write(f"  – Already imported: {dest_filename} for '{product.name}'")
        return False

    is_primary = not ProductImage.objects.filter(product=product).exists()

    if dry_run:
        action = "SET PRIMARY" if is_primary else "add"
        stdout.write(f"  [dry-run] Would {action}: {src_path.name} → {relative} (product: {product.name})")
        return True

    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dest_path)

    ProductImage.objects.create(
        product=product,
        image=relative,
        is_primary=is_primary,
    )

    tag = style.SUCCESS("✓ primary") if is_primary else "✓ added"
    stdout.write(f"  {tag}: {src_path.name} → {relative} (product: {product.name})")
    return True


class Command(BaseCommand):
    help = 'Import local product images into the database from a manifest file or folder.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--manifest', '-m',
            default=None,
            help=f'Path to the manifest .md file (default: {DEFAULT_MANIFEST})',
        )
        parser.add_argument(
            '--folder', '-f',
            default=None,
            help='Path to a folder of images — matched to products by filename.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Show what would be imported without making any changes.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be made.\n'))

        if options['folder']:
            self._import_folder(Path(options['folder']), dry_run)
        else:
            manifest = Path(options['manifest']) if options['manifest'] \
                else Path(settings.BASE_DIR) / DEFAULT_MANIFEST
            self._import_manifest(manifest, dry_run)

    # ── Manifest mode ─────────────────────────────────────────────────────────

    def _import_manifest(self, manifest_path: Path, dry_run: bool):
        if not manifest_path.exists():
            raise CommandError(f'Manifest not found: {manifest_path}')

        self.stdout.write(f'Reading manifest: {manifest_path}\n')
        imported = skipped = errors = 0

        for lineno, raw in enumerate(manifest_path.read_text(encoding='utf-8').splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith('#'):
                continue

            # Expected format:  product name - /path/to/image.ext
            if ' - ' not in line:
                self.stdout.write(self.style.WARNING(
                    f'  Line {lineno}: skipping (no " - " separator): {line!r}'))
                skipped += 1
                continue

            name_hint, _, raw_path = line.partition(' - ')
            name_hint = name_hint.strip()
            src_path  = Path(raw_path.strip())

            # Resolve relative paths against BASE_DIR
            if not src_path.is_absolute():
                src_path = Path(settings.BASE_DIR) / src_path

            if src_path.suffix.lower() not in IMAGE_EXTS:
                self.stdout.write(self.style.WARNING(
                    f'  Line {lineno}: not a recognised image extension: {src_path.suffix}'))
                skipped += 1
                continue

            product = _find_product(name_hint)
            if not product:
                self.stdout.write(self.style.ERROR(
                    f'  Line {lineno}: no product found for "{name_hint}"'))
                errors += 1
                continue

            ok = _import_image(product, src_path, dry_run, self.stdout, self.style)
            if ok:
                imported += 1
            else:
                skipped += 1

        self._summary(imported, skipped, errors, dry_run)

    # ── Folder mode ───────────────────────────────────────────────────────────

    def _import_folder(self, folder: Path, dry_run: bool):
        if not folder.exists() or not folder.is_dir():
            raise CommandError(f'Folder not found: {folder}')

        self.stdout.write(f'Scanning folder: {folder}\n')
        imported = skipped = errors = 0

        image_files = sorted(
            f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTS
        )

        if not image_files:
            self.stdout.write(self.style.WARNING('No image files found in folder.'))
            return

        for src_path in image_files:
            name_hint = _clean_stem(src_path.stem)
            product   = _find_product(name_hint)

            if not product:
                self.stdout.write(self.style.ERROR(
                    f'  No product found for "{name_hint}" ({src_path.name})'))
                errors += 1
                continue

            ok = _import_image(product, src_path, dry_run, self.stdout, self.style)
            if ok:
                imported += 1
            else:
                skipped += 1

        self._summary(imported, skipped, errors, dry_run)

    # ── Summary ───────────────────────────────────────────────────────────────

    def _summary(self, imported, skipped, errors, dry_run):
        self.stdout.write('')
        prefix = '[dry-run] Would import' if dry_run else 'Imported'
        self.stdout.write(self.style.SUCCESS(
            f'{prefix} {imported} image(s).  Skipped: {skipped}.  Errors: {errors}.'))
