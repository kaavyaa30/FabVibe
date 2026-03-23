"""
Celery tasks for the Virtual Try-On feature.

The outfit chain is a long-running process (30–60 s per garment × up to 4 garments).
Running it in a Celery worker keeps the Django request thread free.

Task flow
─────────
1. View saves the uploaded photo to a temp file, enqueues run_vton_task,
   and immediately returns a task_id to the browser.
2. Browser polls /tryon/status/<task_id>/ every 3 s.
3. Worker runs the outfit chain, updating task.meta with step progress.
4. On completion the result URL is stored in the Celery result backend (Django DB).
5. A TryOnHistory record is silently created for the logged-in user.
6. Browser receives the final URL and displays the result.
"""
import os
import shutil
import tempfile
import logging

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

logger = logging.getLogger(__name__)


def _save_original(person_path: str, media_root: str) -> str:
    """
    Copy the user's uploaded photo into media/tryon_originals/ for history storage.
    Returns the relative path (suitable for an ImageField).
    """
    import uuid
    save_dir = os.path.join(media_root, 'tryon_originals')
    os.makedirs(save_dir, exist_ok=True)
    ext      = os.path.splitext(person_path)[1] or '.jpg'
    filename = f"{uuid.uuid4().hex}{ext}"
    dest     = os.path.join(save_dir, filename)
    shutil.copy2(person_path, dest)
    return f"tryon_originals/{filename}"


def _record_history(user_id, product_id, original_rel, result_rel):
    """
    Silently create a TryOnHistory row.  Any DB error is caught and logged
    so it never breaks the task's success return value.
    """
    if not user_id:
        return
    try:
        import django
        from .models import TryOnHistory, Product
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user    = User.objects.get(pk=user_id)
        product = Product.objects.filter(pk=product_id).first() if product_id else None
        TryOnHistory.objects.create(
            user=user,
            product=product,
            original_image=original_rel,
            result_image=result_rel,
        )
        logger.info(f"[VTON history] Saved for user {user_id}, product {product_id}")
    except Exception as e:
        logger.warning(f"[VTON history] Could not save history record: {e}")


@shared_task(
    bind=True,
    name='products.tasks.run_vton_task',
    max_retries=0,               # don't auto-retry — HF queue errors need user action
    time_limit=1800,             # hard kill after 30 min
    soft_time_limit=1500,        # SoftTimeLimitExceeded raised at 25 min
)
def run_vton_task(self, person_path: str, garment_infos: list, media_root: str,
                  user_id: int = None):
    """
    Run the full outfit try-on chain in a background worker.

    Args:
        person_path:   Absolute path to the saved user photo temp file.
        garment_infos: List of dicts {path, category_slug, name, product_id}.
        media_root:    Django MEDIA_ROOT.
        user_id:       ID of the requesting user (for TryOnHistory).

    Returns (stored in result backend):
        {'success': True,  'result_url': 'tryon_results/abc.png'}
        {'success': False, 'error': '…', 'step_failed': N}
    """
    from .tryon_service import _call_hf, _get_hf_client, _save_result, filter_and_sort_garments

    # Filter accessories, apply dress-only mode, sort upper → lower
    garments = filter_and_sort_garments(garment_infos)

    if not garments:
        return {
            'success': False,
            'error': 'No supported clothing items selected. Accessories and unsupported categories are skipped.',
        }

    total              = len(garments)
    current_person     = person_path
    intermediate_files = []

    def _update(step, status_label):
        self.update_state(
            state='PROGRESS',
            meta={'step': step, 'total': total, 'label': status_label},
        )

    try:
        # Create the HF client once — avoids re-fetching the Space API schema
        # on every garment, which is the main source of cold-start latency.
        _update(0, 'Connecting to AI server…')
        try:
            hf_client = _get_hf_client()
        except RuntimeError as e:
            return {'success': False, 'error': str(e), 'step_failed': 0}

        for step, g in enumerate(garments, start=1):
            label = f"Fitting {g['name']}…"
            logger.info(f"[VTON task {self.request.id}] Step {step}/{total}: {g['name']} ({g['vton_category']})")
            _update(step, label)

            try:
                result_local = _call_hf(current_person, g['path'], g['vton_category'], client=hf_client)
            except RuntimeError as e:
                logger.error(f"[VTON task {self.request.id}] HF call failed at step {step}: {e}")
                return {'success': False, 'error': str(e), 'step_failed': step}

            if step < total:
                ext  = os.path.splitext(result_local)[1] or '.png'
                tmp  = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                tmp.close()
                shutil.copy2(result_local, tmp.name)
                intermediate_files.append(tmp.name)
                current_person = tmp.name
            else:
                _update(step, 'Finalizing your look…')
                result_rel   = _save_result(result_local, media_root)
                original_rel = _save_original(person_path, media_root)
                # Use the first garment's product_id as the "primary" product for history
                primary_product_id = garments[0].get('product_id')
                _record_history(user_id, primary_product_id, original_rel, result_rel)
                return {'success': True, 'result_url': result_rel}

    except SoftTimeLimitExceeded:
        logger.warning(f"[VTON task {self.request.id}] Soft time limit exceeded")
        return {
            'success': False,
            'error': 'The try-on took too long and was stopped. Please try with fewer garments.',
            'step_failed': None,
        }
    except Exception as e:
        logger.exception(f"[VTON task {self.request.id}] Unexpected error")
        return {'success': False, 'error': str(e), 'step_failed': None}

    finally:
        for f in intermediate_files:
            try: os.unlink(f)
            except OSError: pass
        try: os.unlink(person_path)
        except OSError: pass
