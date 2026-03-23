"""
Baby / Kids Virtual Try-On — uses diffusers/stable-diffusion-xl-inpainting HF Space.

No local model download. No GPU required. Same pattern as adult IDM-VTON.
"""

import gc
import os
import logging
import tempfile
import shutil
import uuid

logger = logging.getLogger(__name__)


def run_baby_tryon(person_path: str, garment_infos: list,
                   write_state=None) -> str:
    """
    Overlay the first garment onto the baby/child photo using SDXL Inpainting
    via the diffusers/stable-diffusion-xl-inpainting HF Space.

    Returns absolute path to result image.
    Raises RuntimeError with a user-friendly message on failure.
    """
    def _progress(label, step=1, total=3):
        if write_state:
            write_state({'state': 'PROGRESS', 'step': step, 'total': total, 'label': label})

    if not garment_infos:
        raise RuntimeError("No garments provided for baby try-on.")

    garment      = garment_infos[0]
    garment_path = garment['path']
    garment_name = garment.get('name', 'garment')

    try:
        from PIL import Image, ImageDraw
        from gradio_client import Client, handle_file
    except ImportError as e:
        raise RuntimeError(f"Missing dependency: {e}. Run: pip install gradio_client Pillow")

    _progress("Preparing images…", step=1, total=3)

    # ── 1. Resize person image to 1024×1024 (SDXL native) ────────────────────
    person_prep  = _prepare_square(person_path,  1024)
    garment_prep = _prepare_square(garment_path, 512)   # for reference only (prompt)

    # ── 2. Build torso mask ───────────────────────────────────────────────────
    mask_path = _build_mask(1024)

    # ── 3. Build prompt ───────────────────────────────────────────────────────
    prompt = _build_prompt(garment_name, garment.get('category_slug', ''))
    negative = (
        "blurry, distorted, bad anatomy, extra limbs, watermark, "
        "deformed face, ugly, low quality, artifacts"
    )

    # ── 4. Connect to HF Space ────────────────────────────────────────────────
    _progress("Connecting to AI server…", step=2, total=3)

    import django.conf
    hf_token = getattr(django.conf.settings, 'HF_TOKEN', '') or None

    try:
        client = Client(
            "diffusers/stable-diffusion-xl-inpainting",
            token=hf_token,
            verbose=False,
        )
        logger.info("[BabyTryon] Connected to SDXL Inpainting Space.")
    except Exception as e:
        for f in (person_prep, garment_prep, mask_path):
            try: os.unlink(f)
            except OSError: pass
        raise RuntimeError(f"Could not connect to baby try-on AI server: {e}")

    # ── 5. Build ImageEditor dict (background=person, layers=[mask]) ──────────
    # The Space expects an ImageEditor component dict, same pattern as IDM-VTON.
    input_image = {
        "background": handle_file(person_prep),
        "layers":     [handle_file(mask_path)],
        "composite":  handle_file(person_prep),
    }

    _progress(f"Generating try-on for {garment_name}…", step=3, total=3)

    result = None
    try:
        result = client.predict(
            input_image,    # ImageEditor dict
            prompt,         # prompt
            negative,       # negative prompt
            7.5,            # guidance_scale
            20,             # steps
            0.99,           # strength
            "EulerDiscreteScheduler",  # scheduler
            api_name="/predict",
        )
    except RuntimeError as e:
        msg = str(e).lower()
        if "interpreter shutdown" in msg or "cannot schedule" in msg:
            raise RuntimeError(
                "The server was reloaded mid-request. Please try again."
            )
        raise RuntimeError(f"Baby try-on failed: {e}")
    except Exception as e:
        msg = str(e).lower()
        if "queue" in msg or "busy" in msg:
            raise RuntimeError("Baby try-on AI server is busy. Please try again in a moment.")
        if "zerogpu" in msg or "quota" in msg:
            raise RuntimeError("Baby try-on AI quota exceeded. Please try again later.")
        if "interpreter shutdown" in msg or "cannot schedule" in msg:
            raise RuntimeError(
                "The server was reloaded mid-request. Please try again."
            )
        raise RuntimeError(f"Baby try-on failed: {e}")
    finally:
        for f in (person_prep, garment_prep, mask_path):
            try: os.unlink(f)
            except OSError: pass
        gc.collect()

    # ── 6. Extract result path ────────────────────────────────────────────────
    # Space returns a tuple of two image dicts (ImageSlider) — we want index 0
    if not result:
        raise RuntimeError("Baby try-on returned an empty result.")

    output = result
    if isinstance(output, (list, tuple)):
        output = output[0]
    if isinstance(output, dict):
        output = output.get("path") or output.get("url", "")

    if not output or not os.path.exists(str(output)):
        raise RuntimeError(f"Baby try-on output file not found: {output}")

    logger.info(f"[BabyTryon] Result at: {output}")
    return str(output)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _prepare_square(src_path: str, size: int) -> str:
    """Resize + center-crop to size×size, save as JPEG temp file."""
    from PIL import Image
    with Image.open(src_path) as img:
        img = img.convert('RGB')
        w, h = img.size
        scale = max(size / w, size / h)
        nw, nh = round(w * scale), round(h * scale)
        img = img.resize((nw, nh), Image.LANCZOS)
        left = (nw - size) // 2
        top  = (nh - size) // 2
        img  = img.crop((left, top, left + size, top + size))
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        tmp.close()
        img.save(tmp.name, format='JPEG', quality=90)
        return tmp.name


def _build_mask(size: int) -> str:
    """
    White torso/body rectangle on black background — tells the model
    which region to repaint with the new garment.
    """
    from PIL import Image, ImageDraw
    mask = Image.new('RGB', (size, size), (0, 0, 0))
    draw = ImageDraw.Draw(mask)
    # Cover torso area: 15%–85% width, 20%–80% height
    draw.rectangle([
        int(size * 0.15), int(size * 0.20),
        int(size * 0.85), int(size * 0.80),
    ], fill=(255, 255, 255))
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    tmp.close()
    mask.save(tmp.name, format='PNG')
    return tmp.name


def _build_prompt(garment_name: str, category_slug: str) -> str:
    name = garment_name.lower()
    if any(k in name for k in ('dress', 'frock', 'gown', 'set')):
        style = "wearing a cute dress"
    elif any(k in name for k in ('shirt', 'top', 'tee', 't-shirt', 'blouse')):
        style = "wearing a cute shirt"
    elif any(k in name for k in ('jeans', 'pant', 'trouser', 'legging')):
        style = "wearing cute pants"
    elif any(k in name for k in ('jacket', 'coat', 'hoodie', 'sweater')):
        style = "wearing a cute jacket"
    else:
        style = f"wearing {garment_name}"
    return (
        f"A cute baby {style}, photorealistic, high quality, "
        f"soft natural lighting, studio photo, detailed fabric texture, "
        f"same baby face and skin tone"
    )
