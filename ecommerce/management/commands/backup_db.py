"""
Django management command for database backup
Usage: python manage.py backup_db
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import shutil
from datetime import datetime, timedelta
from pathlib import Path


class Command(BaseCommand):
    help = 'Create a backup of the database with timestamp and cleanup old backups'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all available backups',
        )
        parser.add_argument(
            '--retention-days',
            type=int,
            default=30,
            help='Number of days to keep backups (default: 30)',
        )
        parser.add_argument(
            '--max-backups',
            type=int,
            default=50,
            help='Maximum number of backups to keep (default: 50)',
        )

    def handle(self, *args, **options):
        backup_dir = Path(settings.BASE_DIR) / 'backups'
        backup_dir.mkdir(exist_ok=True)

        if options['list']:
            self.list_backups(backup_dir)
            return

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('FabVibe Database Backup'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Create backup
        success = self.create_backup(backup_dir)

        if success:
            # Cleanup old backups
            self.cleanup_old_backups(
                backup_dir,
                options['retention_days'],
                options['max_backups']
            )
            self.stdout.write(self.style.SUCCESS('\n✓ Backup completed successfully!'))
        else:
            self.stdout.write(self.style.ERROR('\n✗ Backup failed!'))

    def create_backup(self, backup_dir):
        """Create a database backup"""
        try:
            db_config = settings.DATABASES['default']
            
            if db_config['ENGINE'] == 'django.db.backends.sqlite3':
                db_path = Path(db_config['NAME'])
                
                if not db_path.exists():
                    self.stdout.write(self.style.ERROR(f'Database file not found: {db_path}'))
                    return False

                # Generate backup filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_filename = f'db_backup_{timestamp}.sqlite3'
                backup_path = backup_dir / backup_filename

                # Copy database
                self.stdout.write(f'Creating backup: {backup_filename}')
                shutil.copy2(db_path, backup_path)

                # Verify
                if backup_path.exists():
                    size = backup_path.stat().st_size
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ Backup created: {backup_filename} ({size:,} bytes)'
                    ))
                    return True
                else:
                    return False
            else:
                self.stdout.write(self.style.ERROR(
                    'This command currently only supports SQLite databases'
                ))
                return False

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            return False

    def cleanup_old_backups(self, backup_dir, retention_days, max_backups):
        """Remove old backups based on retention policy"""
        try:
            backup_files = sorted(backup_dir.glob('db_backup_*.sqlite3'))
            
            if not backup_files:
                return

            self.stdout.write(f'\nFound {len(backup_files)} existing backup(s)')

            # Remove old backups
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            removed_count = 0

            for backup_file in backup_files:
                try:
                    timestamp_str = backup_file.stem.replace('db_backup_', '')
                    backup_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')

                    if backup_date < cutoff_date:
                        self.stdout.write(f'Removing old backup: {backup_file.name}')
                        backup_file.unlink()
                        removed_count += 1
                except ValueError:
                    continue

            # Remove excess backups
            remaining_backups = sorted(backup_dir.glob('db_backup_*.sqlite3'))
            if len(remaining_backups) > max_backups:
                excess_count = len(remaining_backups) - max_backups
                for backup_file in remaining_backups[:excess_count]:
                    self.stdout.write(f'Removing excess backup: {backup_file.name}')
                    backup_file.unlink()
                    removed_count += 1

            if removed_count > 0:
                self.stdout.write(self.style.SUCCESS(f'✓ Removed {removed_count} old backup(s)'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Cleanup error: {str(e)}'))

    def list_backups(self, backup_dir):
        """List all available backups"""
        if not backup_dir.exists():
            self.stdout.write('No backups directory found')
            return

        backup_files = sorted(backup_dir.glob('db_backup_*.sqlite3'), reverse=True)

        if not backup_files:
            self.stdout.write('No backups found')
            return

        self.stdout.write(f'\nAvailable backups ({len(backup_files)}):')
        self.stdout.write('-' * 80)

        for backup_file in backup_files:
            size = backup_file.stat().st_size
            try:
                timestamp_str = backup_file.stem.replace('db_backup_', '')
                backup_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                age_days = (datetime.now() - backup_date).days
                self.stdout.write(
                    f'{backup_file.name:40} {size:>12,} bytes  {age_days:>3} days old'
                )
            except ValueError:
                self.stdout.write(f'{backup_file.name:40} {size:>12,} bytes')

        self.stdout.write('-' * 80)
