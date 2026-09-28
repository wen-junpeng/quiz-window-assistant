import base64
import io

import pytest
from PIL import Image

from quiz_assistant.imaging import prepare_image_data_url


def decode_data_url(value: str) -> Image.Image:
    prefix, encoded = value.split(",", 1)
    assert prefix == "data:image/jpeg;base64"
    return Image.open(io.BytesIO(base64.b64decode(encoded)))


def test_prepare_image_scales_longest_edge_and_preserves_aspect_ratio():
    source = Image.new("RGB", (3200, 1600), "white")

    result = decode_data_url(prepare_image_data_url(source))

    assert result.size == (1600, 800)
    assert result.format == "JPEG"


def test_prepare_image_converts_transparency_to_rgb():
    source = Image.new("RGBA", (20, 10), (255, 0, 0, 128))

    result = decode_data_url(prepare_image_data_url(source))

    assert result.mode == "RGB"
    assert result.size == (20, 10)


@pytest.mark.parametrize(
    ("max_edge", "quality"),
    [(0, 85), (1600, 0), (1600, 101)],
)
def test_prepare_image_rejects_invalid_limits(max_edge, quality):
    source = Image.new("RGB", (20, 10), "white")

    with pytest.raises(ValueError):
        prepare_image_data_url(source, max_edge=max_edge, quality=quality)
