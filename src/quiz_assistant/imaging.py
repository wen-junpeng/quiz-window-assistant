import base64
import io

from PIL import Image


def prepare_image_data_url(
    image: Image.Image, max_edge: int = 1600, quality: int = 85
) -> str:
    if max_edge <= 0:
        raise ValueError("max_edge must be positive")
    if not 1 <= quality <= 100:
        raise ValueError("quality must be between 1 and 100")

    prepared = image.convert("RGB")
    if max(prepared.size) > max_edge:
        scale = max_edge / max(prepared.size)
        size = tuple(max(1, round(value * scale)) for value in prepared.size)
        prepared = prepared.resize(size, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    prepared.save(buffer, format="JPEG", quality=quality, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"
