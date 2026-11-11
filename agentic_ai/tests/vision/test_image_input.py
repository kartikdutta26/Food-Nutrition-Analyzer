"""Synthetic pixels only: these tests make no food-recognition claim."""
from dataclasses import FrozenInstanceError
import hashlib
from io import BytesIO
import struct

from PIL import Image, PngImagePlugin
from pydantic import ValidationError
import pytest

from agentic_ai.schemas.vision import ImageReference, PreprocessingMetadata
from agentic_ai.tools.image_input import ImageInputError, ImageInputSettings, preprocess_image
from agentic_ai.adapters.vision_handoff import validate_recognition_result


def write_image(tmp_path, *, mode="RGB", size=(17, 11), format="PNG", color=None, **options):
    path = tmp_path / ("private-photo.jpg" if format == "JPEG" else "private-photo.png")
    with Image.new(mode, size, color) as image:
        image.save(path, format=format, **options)
    return path


def chunks(data):
    result, offset = [], 8
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset+4])[0]
        result.append(data[offset+4:offset+8])
        offset += 12 + length
    assert offset == len(data)
    return result


@pytest.mark.parametrize("format", ["JPEG", "PNG"])
def test_real_decode_hashes_determinism_and_input_immutability(tmp_path, format):
    path = write_image(tmp_path, format=format, color=(27, 51, 90))
    original = path.read_bytes()
    result = preprocess_image(path, image_id="synthetic-a")
    again = preprocess_image(str(path), image_id="synthetic-a")
    assert result == again
    assert path.read_bytes() == original
    assert result.image.original_sha256 == hashlib.sha256(original).hexdigest()
    assert result.image.byte_size == len(original)
    assert (result.image.width, result.image.height) == (17, 11)
    assert result.image.media_type == ("image/jpeg" if format == "JPEG" else "image/png")
    assert result.preprocessing.processed_sha256 == hashlib.sha256(result.processed_bytes).hexdigest()
    assert result.preprocessing.media_type == "image/png"
    assert isinstance(result.image, ImageReference)
    assert isinstance(result.preprocessing, PreprocessingMetadata)
    assert result.decoder_version == "13.0.0"
    assert result.processor_version == "m5.2-v1"
    assert chunks(result.processed_bytes) == [b"IHDR", b"IDAT", b"IEND"]
    with Image.open(BytesIO(result.processed_bytes)) as processed:
        assert processed.mode == "RGB"
        assert processed.size == (17, 11)
        assert not processed.info and not processed.getexif()
    assert str(path) not in repr(result)
    assert "processed_bytes" not in repr(result)
    with pytest.raises(FrozenInstanceError):
        result.processed_bytes = b"altered"
    with pytest.raises(ValidationError):
        result.image.width = 1


@pytest.mark.parametrize("size,expected", [
    ((2048, 1024), (1024, 512)), ((800, 1600), (512, 1024)),
    ((1200, 800), (1024, 683)), ((1024, 1024), (1024, 1024)),
    ((1, 1), (1, 1)), ((3, 1), (3, 1)), ((1, 20000), (1, 1024)),
])
def test_resize_and_no_upscale(tmp_path, size, expected):
    result = preprocess_image(write_image(tmp_path, size=size))
    assert (result.preprocessing.width, result.preprocessing.height) == expected
    assert (result.image.width, result.image.height) == size


@pytest.mark.parametrize("orientation", range(1, 9))
@pytest.mark.parametrize("format", ["JPEG", "PNG"])
def test_all_exif_orientations_including_mirrors(tmp_path, orientation, format):
    # Distinct pixels detect mirrored transforms as well as swapped dimensions.
    path = tmp_path / ("orientation.jpg" if format == "JPEG" else "orientation.png")
    image = Image.new("RGB", (3, 2))
    image.putdata([(255, 0, 0), (0, 255, 0), (0, 0, 255), (90, 30, 0), (0, 80, 20), (30, 10, 90)])
    exif = Image.Exif()
    exif[274] = orientation
    exif[270] = "PRIVATE IMAGE DESCRIPTION"
    image.save(path, format=format, exif=exif)
    image.close()
    transforms = {2: Image.Transpose.FLIP_LEFT_RIGHT, 3: Image.Transpose.ROTATE_180,
                  4: Image.Transpose.FLIP_TOP_BOTTOM, 5: Image.Transpose.TRANSPOSE,
                  6: Image.Transpose.ROTATE_270, 7: Image.Transpose.TRANSVERSE,
                  8: Image.Transpose.ROTATE_90}
    with Image.open(path) as source:
        rgb = source.convert("RGB")
        expected = rgb.transpose(transforms[orientation]) if orientation in transforms else rgb.copy()
        rgb.close()
    result = preprocess_image(path)
    with Image.open(BytesIO(result.processed_bytes)) as actual:
        assert actual.tobytes() == expected.tobytes()
    expected.close()
    assert (result.image.width, result.image.height) == (3, 2)
    assert result.preprocessing.original_exif_orientation == orientation
    assert (result.preprocessing.width, result.preprocessing.height) == ((2, 3) if orientation >= 5 else (3, 2))
    assert b"PRIVATE" not in result.processed_bytes


@pytest.mark.parametrize("mode,format,color", [
    ("1", "PNG", 1), ("L", "PNG", 127), ("LA", "PNG", (10, 0)),
    ("P", "PNG", 0), ("RGB", "PNG", (3, 5, 7)), ("RGBA", "PNG", (10, 20, 30, 0)),
    ("CMYK", "JPEG", (30, 20, 10, 0)), ("L", "JPEG", 120),
    ("I;16", "PNG", 32768),
])
def test_safe_color_modes(tmp_path, mode, format, color):
    result = preprocess_image(write_image(tmp_path, mode=mode, format=format, color=color))
    with Image.open(BytesIO(result.processed_bytes)) as image:
        assert image.mode == "RGB"
        if mode in {"LA", "RGBA"}:
            assert image.getpixel((0, 0)) == (255, 255, 255)
        if mode == "I;16":
            assert image.getpixel((0, 0)) == (127, 127, 127)


def test_alpha_palette_and_semitransparency(tmp_path):
    path = write_image(tmp_path, mode="P", color=0, transparency=0)
    with Image.open(BytesIO(preprocess_image(path).processed_bytes)) as image:
        assert image.getpixel((0, 0)) == (255, 255, 255)
    path = write_image(tmp_path, mode="RGBA", color=(255, 0, 0, 128))
    with Image.open(BytesIO(preprocess_image(path).processed_bytes)) as image:
        assert image.getpixel((0, 0)) == (255, 127, 127)


@pytest.mark.parametrize("format", ["JPEG", "PNG"])
def test_metadata_gps_exif_icc_comments_and_text_are_stripped(tmp_path, format):
    exif = Image.Exif()
    exif[274] = 6
    exif[270] = "PRIVATE_DESCRIPTION"
    exif[34853] = {1: "N", 2: (1, 2, 3), 3: "E", 4: (4, 5, 6)}
    options = {"exif": exif, "icc_profile": b"PRIVATE_ICC", "dpi": (300, 300)}
    if format == "PNG":
        info = PngImagePlugin.PngInfo()
        info.add_text("Comment", "PRIVATE_COMMENT")
        info.add_itxt("XML:com.adobe.xmp", "PRIVATE_XMP")
        info.add_text("Author", "PRIVATE_AUTHOR", zip=True)
        options["pnginfo"] = info
    else:
        options["comment"] = b"PRIVATE_COMMENT"
    path = write_image(tmp_path, format=format, **options)
    original = path.read_bytes()
    result = preprocess_image(path)
    assert path.read_bytes() == original
    assert result.preprocessing.metadata_removed is True
    assert chunks(result.processed_bytes) == [b"IHDR", b"IDAT", b"IEND"]
    with Image.open(BytesIO(result.processed_bytes)) as decoded:
        assert not decoded.info and not decoded.getexif()


def test_configured_smaller_edges_are_deterministic(tmp_path):
    path = write_image(tmp_path, size=(1200, 800))
    settings = ImageInputSettings(max_output_edge=256)
    result = preprocess_image(path, settings=settings)
    assert (result.preprocessing.width, result.preprocessing.height) == (256, 171)
    assert result == preprocess_image(path, settings=settings)


def test_default_metadata_fits_unchanged_full_m51_contract(tmp_path, result_data):
    path = write_image(tmp_path, size=(1200, 800), exif=Image.Exif())
    result = preprocess_image(path, image_id="synthetic-a")
    result_data["image"] = result.image.model_dump(mode="json")
    result_data["preprocessing"] = result.preprocessing.model_dump(mode="json")
    validated = validate_recognition_result(result_data)
    assert validated.preprocessing == result.preprocessing
    assert validated.image == result.image


def test_smaller_policy_is_not_misrepresented_as_fixed_m51_policy(tmp_path, result_data):
    result = preprocess_image(write_image(tmp_path, size=(1200, 800)),
                              settings=ImageInputSettings(max_output_edge=256))
    result_data["image"] = result.image.model_dump(mode="json")
    result_data["preprocessing"] = result.preprocessing.model_dump(mode="json")
    from agentic_ai.vision_errors import VisionContractError
    with pytest.raises(VisionContractError):
        validate_recognition_result(result_data)


@pytest.mark.parametrize("orientation", [5, 6, 7, 8])
def test_oriented_resizing_fits_m51(tmp_path, result_data, orientation):
    exif = Image.Exif()
    exif[274] = orientation
    result = preprocess_image(write_image(tmp_path, size=(1200, 800), exif=exif))
    result_data["image"] = result.image.model_dump(mode="json")
    result_data["preprocessing"] = result.preprocessing.model_dump(mode="json")
    assert validate_recognition_result(result_data).preprocessing.width == 683


def test_content_ids_do_not_depend_on_private_filenames(tmp_path):
    first = write_image(tmp_path)
    other = tmp_path / "another-private-name.PNG"
    other.write_bytes(first.read_bytes())
    a, b = preprocess_image(first), preprocess_image(other)
    assert a == b
    assert a.image.image_id == "img-" + a.image.original_sha256[:24]


def test_metadata_changes_source_hash_but_not_processed_pixels(tmp_path):
    first = write_image(tmp_path, color=(1, 2, 3))
    a = preprocess_image(first)
    info = PngImagePlugin.PngInfo()
    info.add_text("private", "not retained")
    b = preprocess_image(write_image(tmp_path, color=(1, 2, 3), pnginfo=info))
    assert a.image.original_sha256 != b.image.original_sha256
    assert a.processed_bytes == b.processed_bytes
    assert a.preprocessing.processed_sha256 == b.preprocessing.processed_sha256
