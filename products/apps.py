from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'

    def ready(self):
        """Clean up stale try-on state files on server start."""
        import os, glob, json, time
        try:
            from django.conf import settings
            state_dir = os.path.join(settings.MEDIA_ROOT, 'tryon_state')
            if not os.path.isdir(state_dir):
                return
            now = time.time()
            for f in glob.glob(os.path.join(state_dir, '*.json')):
                try:
                    age = now - os.path.getmtime(f)
                    with open(f) as fp:
                        state = json.load(fp).get('state', '')
                    # Remove completed/failed tasks, or anything older than 10 min
                    if state in ('FAILURE', 'SUCCESS') or age > 600:
                        os.unlink(f)
                except Exception:
                    try:
                        os.unlink(f)
                    except Exception:
                        pass
        except Exception:
            pass
