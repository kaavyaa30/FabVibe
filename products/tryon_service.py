"""
Virtual Try-On service — yisol/IDM-VTON on Hugging Face Spaces.

Category mapping
────────────────
IDM-VTON accepts exactly three category strings:
    'upper_body'  — tops, shirts, jackets, t-shirts
    'lower_body'  — jeans, skirts, trousers
    'dresses'     — one-piece dresses (skips all other items when selected)

Accessories (sunglasses, watches, belts, bags, shoes, heels) are filtered out
before the chain runs — the model produces artifacts on non-clothing items.

Image pre-processing
────────────────────
Both person and garment images are resized/center-cropped to 768×1024 (3:4)
before being sent to the HF Space.  This matches IDM-VTON's native resolution,
reduces upload size, and prevents the smoky/distorted artefacts that appear
when the model receives oddly-shaped inputs.
"""
import os
import uuid
import shutil
import tempfile
import logging

logger = logging.getLogger(__name__)

# ── Category slug → IDM-VTON category string ─────────────────────────────────
# Slugs that map to a supported VTON category
SLUG_TO_VTON_CATEGORY = {
    # Upper body
    'women-tops':    'upper_body',
    'men-shirts':    'upper_body',
    'men-t-shirts':  'upper_body',
    'men-jackets':   'upper_body',
    'boys-shirts':   'upper_body',
    'girls-tops':    'upper_body',
    # Lower body
    'women-skirts':  'lower_body',
    'men-jeans':     'lower_body',
    'boys-jeans':    'lower_body',
    'girls-skirts':  'lower_body',
    # Dresses (one-piece — triggers dress-only mode)
    'women-dresses': 'dresses',
    'girls-dresses': 'dresses',
    # kids-girls is a broad catch-all slug — actual category resolved by name keywords
    'kids-girls':    'dresses',  # fallback only; _resolve_vton_category overrides this
}

# ── Name-based keyword fallback ───────────────────────────────────────────────
# When a category slug is too broad (e.g. kids-girls covers dresses, skirts,
# leggings, tops), use the product name to determine the correct VTON category.
_UPPER_KEYWORDS = {'top', 'shirt', 'blouse', 'jacket', 'tee', 't-shirt', 'sweater',
                   'hoodie', 'sweatshirt', 'coat', 'vest', 'cardigan', 'tunic'}
_LOWER_KEYWORDS = {'jeans', 'skirt', 'trouser', 'pant', 'legging', 'leggings', 'shorts',
                   'bottom', 'culotte', 'capri'}
_DRESS_KEYWORDS = {'dress', 'gown', 'frock', 'jumpsuit', 'romper', 'onesie', 'set'}

# Slugs where name-based resolution should be attempted before using the slug default
_BROAD_SLUGS = {'kids-girls', 'kids-boys', 'kids', 'kids-infants'}


def _resolve_vton_category(slug: str, name: str) -> str | None:
    """
    Return the IDM-VTON category for a garment, using name keywords for broad slugs.
    Returns None if the item should be skipped (accessory / unknown).
    """
    if slug in ACCESSORY_SLUGS:
        return None

    # For broad slugs, try to infer from the product name first
    if slug in _BROAD_SLUGS:
        name_lower = name.lower()
        words = set(name_lower.replace('-', ' ').split())
        if words & _LOWER_KEYWORDS:
            return 'lower_body'
        if words & _UPPER_KEYWORDS:
            return 'upper_body'
        if words & _DRESS_KEYWORDS:
            return 'dresses'
        # Name didn't match — fall through to slug default (dresses for kids-girls)

    return SLUG_TO_VTON_CATEGORY.get(slug)


# Slugs that are accessories — silently skipped, never sent to the model
ACCESSORY_SLUGS = {
    'accessories-sunglasses',
    'accessories-watches',
    'accessories-belts',
    'accessories-bags',
    'women-heels',
    'men-shoes',
    'kids-boys',      # shoes/accessories subcategory
    'accessories',
}


def filter_and_sort_garments(garment_infos: list) -> list:
    """
    Given a list of dicts  {path, category_slug, name},  return a filtered,
    ordered list ready for the VTON chain.

    Rules applied:
    1. Drop any item whose slug is in ACCESSORY_SLUGS.
    2. Drop any item whose slug has no IDM-VTON mapping (unknown category).
    3. If a 'dresses' item is present, keep ONLY that item (dress-only mode).
    4. Order: upper_body first, then lower_body.

    Each returned dict gains a 'vton_category' key.
    """
    # Step 1 — attach vton_category, drop accessories and unknowns
    valid = []
    for g in garment_infos:
        slug = g.get('category_slug', '')
        if slug in ACCESSORY_SLUGS:
            logger.info(f"[VTON filter] Skipping accessory: {g['name']} ({slug})")
            continue
        vton_cat = _resolve_vton_category(slug, g.get('name', ''))
        if not vton_cat:
            logger.info(f"[VTON filter] No VTON mapping for slug '{slug}' / name '{g['name']}', skipping")
            continue
        logger.info(f"[VTON filter] {g['name']} ({slug}) → {vton_cat}")
        valid.append({**g, 'vton_category': vton_cat})

    if not valid:
        return []

    # Step 2 — dress-only mode: if any dress is present, keep only the first dress
    dresses = [g for g in valid if g['vton_category'] == 'dresses']
    if dresses:
        logger.info(f"[VTON filter] Dress detected — dress-only mode, keeping: {dresses[0]['name']}")
        return [dresses[0]]

    # Step 3 — order: upper_body before lower_body
    order = {'upper_body': 0, 'lower_body': 1}
    valid.sort(key=lambda g: order.get(g['vton_category'], 9))
    return valid


# ── Image pre-processing ─────────────────────────────────────────────────────

# IDM-VTON's native resolution — always send images at this exact size.
_VTON_W, _VTON_H = 768, 1024   # native 3:4 portrait

def _prepare_image(src_path: str, width: int = _VTON_W, height: int = _VTON_H,
                   quality: int = 92) -> str:
    """
    Resize *src_path* to fit within *width × height* (letterbox/pillarbox with
    white padding), then save as JPEG.

    Using fit-with-padding instead of scale-to-fill prevents the person from
    being cropped out of frame — the most common cause of OpenPose step-1 failures.
    """
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    with Image.open(src_path) as img:
        img = img.convert('RGB')
        src_w, src_h = img.size

        # Scale to FIT inside target (no cropping — preserve full body)
        scale = min(width / src_w, height / src_h)
        new_w = round(src_w * scale)
        new_h = round(src_h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

        # Paste onto white canvas centered
        canvas = Image.new('RGB', (width, height), (255, 255, 255))
        offset_x = (width  - new_w) // 2
        offset_y = (height - new_h) // 2
        canvas.paste(img, (offset_x, offset_y))

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        tmp.close()
        canvas.save(tmp.name, format='JPEG', quality=quality, optimize=True)
        logger.debug(f"[VTON prep] {src_path} → {width}×{height} padded JPEG @ q{quality} → {tmp.name}")
        return tmp.name


# ── Low-level single HF call ──────────────────────────────────────────────────

def _get_hf_client():
    """
    Return a cached Hugging Face gradio Client.
    Creating the Client fetches the Space API schema — doing it once per task
    (rather than once per garment) eliminates the biggest cold-start delay.
    """
    try:
        from gradio_client import Client
    except ImportError:
        raise RuntimeError("gradio_client is not installed. Run: pip install gradio_client")

    import django.conf
    hf_token = getattr(django.conf.settings, 'HF_TOKEN', '') or ''
    try:
        client = Client("yisol/IDM-VTON", token=hf_token or None, verbose=False)
        logger.info("[VTON] HF Space client connected.")
        return client
    except Exception as e:
        raise RuntimeError(f"Could not connect to HF Space: {e}")


def _call_hf(person_path: str, garment_path: str, vton_category: str = 'upper_body',
             client=None) -> str:
    """
    Make one IDM-VTON API call.

    Pass a pre-created *client* to avoid re-fetching the Space API schema on
    every garment (the main source of cold-start latency).

    Args:
        person_path:    Absolute path to person image.
        garment_path:   Absolute path to garment image.
        vton_category:  'upper_body' | 'lower_body' | 'dresses'
        client:         Optional pre-created gradio Client (created if None).

    Returns:
        Local filesystem path of the output image (temp file from gradio_client).
    Raises:
        RuntimeError with a user-friendly message.
    """
    try:
        from gradio_client import handle_file
    except ImportError:
        raise RuntimeError("gradio_client is not installed. Run: pip install gradio_client")

    if client is None:
        client = _get_hf_client()

    # Pre-process both images to 768×1024 JPEG before sending
    person_prep  = None
    garment_prep = None
    result       = None
    try:
        person_prep  = _prepare_image(person_path)
        garment_prep = _prepare_image(garment_path)

        descriptions = {
            'upper_body': 'A person wearing this top/shirt',
            'lower_body': 'A person wearing these bottoms',
            'dresses':    'A person wearing this dress',
        }
        description = descriptions.get(vton_category, 'A person wearing the garment')

        try:
            result = client.predict(
                {"background": handle_file(person_prep), "layers": [], "composite": handle_file(person_prep)},
                handle_file(garment_prep),
                description,
                True,              # is_checked — auto-masking
                True,              # is_checked_crop — enable auto-crop to isolate person
                30,                # denoise steps
                42,                # seed
                api_name="/tryon",
            )
        except TimeoutError:
            raise RuntimeError("HF Space timed out. The queue is busy — please try again.")
        except Exception as e:
            msg = str(e).lower()
            raw = str(e)
            logger.error(f"[VTON] Raw HF exception: {raw!r}")
            if "queue" in msg or "busy" in msg or "too many" in msg:
                raise RuntimeError("HF Space queue is full. Please wait a few seconds and retry.")
            if "rate" in msg or "limit" in msg:
                raise RuntimeError("HF Space rate limit reached. Please wait a minute before retrying.")
            if "zerogpu" in msg or "quota" in msg or "unlogged" in msg:
                raise RuntimeError("Hugging Face ZeroGPU daily quota exceeded. The free GPU limit has been reached — please try again tomorrow or after a few hours.")
            if "attributeerror" in msg or "step 1" in msg or "keypoint" in msg or "pose" in msg or "nonetype" in msg:
                raise RuntimeError("Could not detect a human body in your photo. Please use a clear, front-facing photo of an adult standing upright.")
            if "interpreter shutdown" in msg or "cannot schedule" in msg:
                raise RuntimeError("Server was reloaded during generation. Please try again.")
            raise RuntimeError(f"IDM-VTON inference failed: {e}")

    finally:
        # Always clean up pre-processed temp files
        for f in (person_prep, garment_prep):
            if f:
                try: os.unlink(f)
                except OSError: pass

    if not result or not isinstance(result, (list, tuple)) or not result[0]:
        raise RuntimeError("IDM-VTON returned an empty result.")

    # IDM-VTON returns [result_image, masked_image] — we want index 0 (the try-on result)
    # result[0] is the final try-on image, result[1] is the mask overlay
    output = result[0]
    logger.info(f"[VTON] Raw result type: {type(result)}, len: {len(result) if hasattr(result, '__len__') else 'N/A'}")
    logger.info(f"[VTON] result[0]: {result[0]}")
    if isinstance(output, dict):
        output = output.get("path") or output.get("url", "")

    if not output or not os.path.exists(str(output)):
        raise RuntimeError(f"Output file not found at: {output}")

    logger.info(f"[VTON] Using output path: {output}")
    return str(output)


# ── Save helper ───────────────────────────────────────────────────────────────

def _save_result(local_path: str, media_root: str) -> str:
    """Copy result to media/tryon_results/ and return the relative URL."""
    save_dir = os.path.join(media_root, "tryon_results")
    os.makedirs(save_dir, exist_ok=True)
    ext      = os.path.splitext(local_path)[1] or ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    dest     = os.path.join(save_dir, filename)
    shutil.copy2(local_path, dest)
    logger.info(f"[VTON] Saved → {dest}")
    return f"tryon_results/{filename}"
