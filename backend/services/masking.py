import replicate
import requests
import os
import uuid
import io
from urllib.parse import urlparse
import time

REPLICATE_MASK_MODEL = os.getenv("REPLICATE_MASK_MODEL", "schananas/grounded_sam")
REPLICATE_MASK_VERSION = os.getenv("REPLICATE_MASK_VERSION", "").strip()

try:
    # replicate-python exports ModelError here
    from replicate.exceptions import ModelError
    from replicate.exceptions import ReplicateError
except Exception:  # pragma: no cover
    ModelError = Exception
    ReplicateError = Exception


class MaskingError(Exception):
    """Base masking exception with a stable error code."""

    def __init__(self, message, code="MASKING_FAILED", details=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class MaskNoDetectionsError(MaskingError):
    def __init__(self, message, details=None):
        super().__init__(message, code="MASK_NO_DETECTIONS", details=details)


def _is_no_detections_model_error(message: str) -> bool:
    msg = (message or "").lower()
    return (
        "cannot reshape tensor of 0 elements" in msg
        or "reshape tensor of 0 elements" in msg
        or "0 elements into shape" in msg
    )


def _is_rate_limit_error(message: str) -> bool:
    msg = (message or "").lower()
    return "status: 429" in msg or "request was throttled" in msg or "rate limit" in msg


def _replicate_error_details(err: Exception):
    details = {}
    pred = getattr(err, "prediction", None)
    if pred is not None:
        details["replicate_prediction_id"] = getattr(pred, "id", None)
        # logs can be large; keep it for server-side debugging
        details["replicate_logs"] = getattr(pred, "logs", None)
    return details


def _build_prompt_candidates(prompt: str):
    base = (prompt or "").strip()
    if not base:
        return []

    candidates = [base]
    normalized = " ".join(base.split()).lower()

    # Grounded-SAM can miss specific terms; this alias set increases hit rate for headphone products.
    if "headphone" in normalized or "headset" in normalized or "earphone" in normalized or "earbud" in normalized:
        candidates.append("headphones, headset, earphones, earbuds")
        candidates.append("over-ear headphones, wireless headset, earphones")

    # Fallback to a broader wearable context only as last resort.
    candidates.append(f"{base}, wearable accessory")

    deduped = []
    seen = set()
    for item in candidates:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def _resolve_mask_model_ref():
    """
    Return a model reference string usable by replicate.run.
    If REPLICATE_MASK_VERSION is set, use it. Otherwise, use latest version.
    """
    if REPLICATE_MASK_VERSION:
        return f"{REPLICATE_MASK_MODEL}:{REPLICATE_MASK_VERSION}"

    model = replicate.models.get(REPLICATE_MASK_MODEL)
    versions = model.versions.list()
    if not versions:
        raise ValueError(f"No versions found for model {REPLICATE_MASK_MODEL}")
    latest_version_id = versions[0].id
    return f"{REPLICATE_MASK_MODEL}:{latest_version_id}"


def _normalize_mask_output(output):
    """
    Replicate may return a direct URL, list, dict, or a generator/iterator.
    Convert to a single mask URL string.
    """
    if output is None:
        return None

    # If it's a generator/iterator (e.g., Prediction.output_iterator), consume it.
    if hasattr(output, "__iter__") and not isinstance(output, (str, bytes, list, dict)):
        try:
            output = list(output)
        except TypeError:
            # Not actually iterable in a consumable way
            output = str(output)

    if isinstance(output, list):
        return output[0] if output else None
    if isinstance(output, dict):
        return output.get("mask") or output.get("output")

    return str(output)


def _prepare_image_input(template_url):
    """
    Replicate needs a publicly accessible URL or a file-like object.
    If the URL is localhost, fetch it server-side and pass the bytes.
    """
    if not isinstance(template_url, str):
        return template_url

    if template_url.startswith("http://") or template_url.startswith("https://"):
        parsed = urlparse(template_url)
        host = (parsed.hostname or "").lower()
        if host in {"localhost", "127.0.0.1"}:
            resp = requests.get(template_url)
            resp.raise_for_status()
            return io.BytesIO(resp.content)
        return template_url

    return template_url


def _run_mask_prediction(model_ref, image_input, prompt, adjustment_factor=20):
    return replicate.run(
        model_ref,
        input={
            "image": image_input,
            "mask_prompt": prompt,
            "adjustment_factor": adjustment_factor,
        }
    )


def _generate_mask_with_prompt_fallbacks(template_url, base_prompt, output_dir):
    model_ref = _resolve_mask_model_ref()
    image_input = _prepare_image_input(template_url)
    prompt_candidates = _build_prompt_candidates(base_prompt)

    last_no_detection_details = None
    saw_rate_limit = False
    for idx, prompt in enumerate(prompt_candidates):
        print(f"[Masking] Attempt {idx + 1}/{len(prompt_candidates)} with prompt: '{prompt}'")
        try:
            output = _run_mask_prediction(model_ref, image_input, prompt, adjustment_factor=20)
            mask_url = _normalize_mask_output(output)
            if not mask_url:
                continue

            print(f"[Masking] Mask generated: {mask_url}")
            response = requests.get(mask_url)
            if response.status_code != 200:
                raise ValueError(f"Failed to download mask image: HTTP {response.status_code}")

            mask_filename = f"mask_{uuid.uuid4()}.png"
            mask_path = os.path.join(output_dir, mask_filename)
            with open(mask_path, "wb") as f:
                f.write(response.content)

            print(f"[Masking] Mask saved to: {mask_path}")
            return mask_path, mask_url

        except ModelError as e:
            details = _replicate_error_details(e)
            msg = str(e)
            if _is_no_detections_model_error(msg):
                last_no_detection_details = details
                continue
            raise MaskingError("Mask model failed to generate a mask.", code="MASK_MODEL_ERROR", details=details)
        except ReplicateError as e:
            msg = str(e)
            if _is_rate_limit_error(msg):
                # Respect low-credit rate limits with a short backoff.
                saw_rate_limit = True
                time.sleep(2.5)
                continue
            raise MaskingError("Replicate request failed while generating mask.", code="MASK_REPLICATE_ERROR")

    if saw_rate_limit and last_no_detection_details is None:
        raise MaskingError(
            "Replicate is temporarily rate-limiting mask requests. Please wait a few seconds and try again.",
            code="MASK_RATE_LIMITED",
        )

    prompt_text = ", ".join(prompt_candidates)
    raise MaskNoDetectionsError(
        "Mask model returned no detections for the provided template. "
        f"Tried prompts: {prompt_text}. Try a clearer template image where the product is larger/visible.",
        details=last_no_detection_details,
    )


def generate_mask(template_url, output_dir="generated"):
    """
    Use a segmentation model on Replicate to auto-detect and mask the main object
    in the template image. Returns the local path of the generated mask image.

    Uses the SAM (Segment Anything Model) via Replicate to create a binary mask
    of the primary object in the image.
    """
    os.makedirs(output_dir, exist_ok=True)

    print(f"[Masking] Generating mask for template: {template_url}")

    try:
        return _generate_mask_with_prompt_fallbacks(
            template_url=template_url,
            base_prompt="shoes, sneakers, footwear, boots",
            output_dir=output_dir,
        )

    except ModelError as e:
        details = _replicate_error_details(e)
        msg = str(e)
        if _is_no_detections_model_error(msg):
            raise MaskNoDetectionsError(
                "Mask model returned no detections for prompt "
                "'shoes, sneakers, footwear, boots'. Try a different description or a clearer template image.",
                details=details,
            )
        raise MaskingError("Mask model failed to generate a mask.", code="MASK_MODEL_ERROR", details=details)
    except Exception as e:
        print(f"[Masking] Error generating mask: {str(e)}")
        raise


def generate_mask_with_description(template_url, object_description, output_dir="generated"):
    """
    Generate a mask using a custom object description.
    Useful when the product isn't shoes (e.g., 'watch', 'bag', 'hat').
    """
    os.makedirs(output_dir, exist_ok=True)

    print(f"[Masking] Generating mask for '{object_description}' in template: {template_url}")

    try:
        return _generate_mask_with_prompt_fallbacks(
            template_url=template_url,
            base_prompt=object_description,
            output_dir=output_dir,
        )

    except ModelError as e:
        details = _replicate_error_details(e)
        msg = str(e)
        if _is_no_detections_model_error(msg):
            prompt = (object_description or "").strip()
            raise MaskNoDetectionsError(
                f"Mask model returned no detections for prompt '{prompt}'. "
                "Check spelling and try synonyms (e.g., 'headphones, headset, earphones') or use a clearer template image.",
                details=details,
            )
        raise MaskingError("Mask model failed to generate a mask.", code="MASK_MODEL_ERROR", details=details)
    except Exception as e:
        print(f"[Masking] Error generating mask: {str(e)}")
        raise
