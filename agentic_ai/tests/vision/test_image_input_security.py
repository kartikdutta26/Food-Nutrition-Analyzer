"""Image security boundaries using small, generated local fixtures."""
import builtins
from io import BytesIO
import os
from pathlib import Path
import struct
from types import SimpleNamespace
import zlib

from PIL import Image, ImageFile, PngImagePlugin
from pydantic import ValidationError
import pytest

from agentic_ai.tools import image_input
from agentic_ai.tools.image_input import ImageInputError, ImageInputSettings, preprocess_image
from .test_image_input import write_image


def fails(path, code=None, **kwargs):
    with pytest.raises(ImageInputError) as caught:
        preprocess_image(path, **kwargs)
    if code:
        assert caught.value.code == code
    if str(path):
        assert str(path) not in str(caught.value)
    return caught.value


@pytest.mark.parametrize("field,values", [
    ("max_input_bytes", [0, -1, 10_485_761, True, "1024", 1.0, None]),
    ("max_decoded_pixels", [0, -1, 20_000_001, True, "1024", float("inf"), None]),
    ("max_output_edge", [0, -1, 1025, True, "512", 512.0, None]),
    ("max_output_bytes", [0, -1, 4_194_305, True, "1024", float("nan"), None]),
])
def test_strict_settings_cannot_raise_hard_limits(field, values):
    for value in values:
        with pytest.raises(ValidationError):
            ImageInputSettings(**{field: value})


@pytest.mark.parametrize("settings", [{}, "1024", True, 1024])
def test_settings_require_validated_model(tmp_path, settings):
    fails(write_image(tmp_path), "invalid_settings", settings=settings)


def test_forged_settings_are_revalidated(tmp_path):
    settings = ImageInputSettings.model_construct(max_input_bytes=99_999_999)
    fails(write_image(tmp_path), "invalid_settings", settings=settings)


@pytest.mark.parametrize("identifier", ["", "private/path", "x"*33, "Photo", 3, True, "a\x00"])
def test_invalid_reference_is_sanitized_before_reading(tmp_path, identifier):
    fails(tmp_path / "unread.png", "invalid_reference", image_id=identifier)


@pytest.mark.parametrize("path", [
    "", "\x00secret", "https://example.invalid/image.png", "file:///private/image.png",
    r"\\server\private\photo.png", "//server/private/photo.png", r"\\?\C:\photo.png",
    r"\\.\NUL", "photo.png:stream", "CON.png", "NUL.jpg", "LPT1.png",
    "COM3.jpg", "private. /photo.png", "photo.png ", "private/photo.png.",
    "x"*4097, b"image.png", None, 17,
])
def test_remote_device_ambiguous_and_invalid_paths_are_rejected(path):
    fails(path, "invalid_path")


def test_unreadable_and_directory_paths(tmp_path):
    fails(tmp_path / "missing.png", "unreadable_image")
    folder = tmp_path / "private.png"
    folder.mkdir()
    fails(folder)  # Windows denies open; POSIX fstat rejects the directory.


@pytest.mark.parametrize("format,extension", [("GIF", ".gif"), ("BMP", ".bmp"), ("TIFF", ".tiff")])
def test_unsupported_containers_even_when_renamed(tmp_path, format, extension):
    path = tmp_path / ("private"+extension)
    with Image.new("RGB", (3, 3)) as image:
        image.save(path, format=format)
    fails(path, "unsupported_format")
    renamed = path.with_suffix(".png")
    renamed.write_bytes(path.read_bytes())
    fails(renamed, "unsupported_format")


@pytest.mark.parametrize("suffix", [".jpg", ".txt", ""])
def test_extension_must_match_container(tmp_path, suffix):
    original = write_image(tmp_path)
    path = tmp_path / ("mismatch"+suffix)
    path.write_bytes(original.read_bytes())
    fails(path, "unsupported_format")


def test_png_and_jpeg_names_are_not_case_sensitive(tmp_path):
    path = write_image(tmp_path, format="JPEG")
    upper = path.with_suffix(".JPEG")
    upper.write_bytes(path.read_bytes())
    assert preprocess_image(upper).image.media_type == "image/jpeg"


@pytest.mark.parametrize("format", ["JPEG", "PNG"])
@pytest.mark.parametrize("damage", ["truncate", "append", "header_only", "random"])
def test_corrupt_truncated_and_trailing_payloads(tmp_path, format, damage):
    path = write_image(tmp_path, format=format)
    data = path.read_bytes()
    if damage == "truncate":
        data = data[:-5]
    elif damage == "append":
        data += b"PRIVATE_TRAILING_PAYLOAD"
    elif damage == "header_only":
        data = data[:10]
    else:
        data = b"not an image"
    path.write_bytes(data)
    fails(path)


def test_png_crc_corruption_is_rejected(tmp_path):
    path = write_image(tmp_path)
    data = bytearray(path.read_bytes())
    data[29] ^= 1  # IHDR CRC, leaving size readable.
    path.write_bytes(data)
    fails(path, "invalid_image")


def test_truncated_jpeg_with_preserved_end_marker_is_rejected(tmp_path):
    path = write_image(tmp_path, format="JPEG", size=(80, 80))
    data = path.read_bytes()
    path.write_bytes(data[:len(data)//2] + b"\xff\xd9")
    fails(path, "invalid_image")


@pytest.mark.parametrize("format", ["JPEG", "PNG"])
@pytest.mark.parametrize("payload", ["duplicate_image", "junk_and_end_marker"])
def test_valid_end_marker_cannot_hide_trailing_payload(tmp_path, format, payload):
    path = write_image(tmp_path, format=format)
    data = path.read_bytes()
    ending = b"\xff\xd9" if format == "JPEG" else b"\x00\x00\x00\x00IEND\xaeB`\x82"
    path.write_bytes(data + (data if payload == "duplicate_image" else b"PRIVATE_PAYLOAD" + ending))
    fails(path, "invalid_image")


@pytest.mark.parametrize("kind", [b"acTL", b"fcTL", b"fdAT", b"IHDR"])
def test_invalid_late_animation_or_duplicate_header_is_rejected(tmp_path, kind):
    path = write_image(tmp_path)
    data = path.read_bytes()
    value = struct.pack(">II", 1, 0) if kind == b"acTL" else b""
    chunk = struct.pack(">I", len(value)) + kind + value + struct.pack(">I", zlib.crc32(kind+value))
    path.write_bytes(data[:-12] + chunk + data[-12:])
    fails(path, "invalid_image" if kind == b"IHDR" else "animated_image")


def test_progressive_jpeg_and_embedded_marker_bytes_are_supported(tmp_path):
    # An EOI byte pair inside EXIF is metadata, not the JPEG end marker.
    exif = Image.Exif()
    exif[37510] = b"binary\xff\xd9metadata"
    path = write_image(tmp_path, format="JPEG", progressive=True, exif=exif)
    assert preprocess_image(path).image.media_type == "image/jpeg"


@pytest.mark.parametrize("frames", [1, 2, 3])
def test_all_apngs_rejected_even_single_frame(tmp_path, frames):
    path = tmp_path / "animation.png"
    images = [Image.new("RGB", (5, 5), (i*30, 0, 0)) for i in range(frames)]
    images[0].save(path, format="PNG", save_all=True, append_images=images[1:], loop=0, duration=100)
    for image in images:
        image.close()
    if frames == 1:
        # Pillow optimizes a one-frame save into ordinary PNG. Construct the
        # actual APNG control chunks to exercise one-frame animation rejection.
        data = path.read_bytes()
        def chunk(kind, value):
            return struct.pack(">I", len(value)) + kind + value + struct.pack(">I", zlib.crc32(kind+value))
        controls = chunk(b"acTL", struct.pack(">II", 1, 0))
        controls += chunk(b"fcTL", struct.pack(">IIIIIHHBB", 0, 5, 5, 0, 0, 1, 10, 0, 0))
        path.write_bytes(data[:33] + controls + data[33:])
    fails(path, "animated_image")


def test_mpo_not_accepted_as_jpeg(tmp_path):
    path = tmp_path / "multiple.jpg"
    with Image.new("RGB", (5, 5)) as first, Image.new("RGB", (5, 5), "red") as second:
        first.save(path, format="MPO", save_all=True, append_images=[second])
    fails(path, "unsupported_format")


def test_input_byte_limits_are_inclusive_and_lowerable(tmp_path):
    path = write_image(tmp_path)
    size = path.stat().st_size
    assert preprocess_image(path, settings=ImageInputSettings(max_input_bytes=size))
    fails(path, "input_size_limit", settings=ImageInputSettings(max_input_bytes=size-1))
    path.write_bytes(b"")
    fails(path, "input_size_limit")


def test_default_input_hard_ceiling_checked_before_decode(tmp_path, monkeypatch):
    path = tmp_path / "oversized.png"
    with path.open("wb") as output:
        output.truncate(10_485_761)
    monkeypatch.setattr(image_input, "_pillow", lambda: pytest.fail("Oversize input reached decoder"))
    fails(path, "input_size_limit")


def test_bounded_read_survives_file_growth_or_incorrect_stat(tmp_path, monkeypatch):
    path = write_image(tmp_path)
    original_fstat = os.fstat
    def short_stat(fd):
        info = original_fstat(fd)
        return SimpleNamespace(st_mode=info.st_mode, st_size=1)
    monkeypatch.setattr(image_input.os, "fstat", short_stat)
    fails(path, "input_size_limit", settings=ImageInputSettings(max_input_bytes=8))


def altered_png_size(path, width, height):
    data = bytearray(path.read_bytes())
    data[16:24] = struct.pack(">II", width, height)
    data[29:33] = struct.pack(">I", zlib.crc32(data[12:29]))
    path.write_bytes(data)


@pytest.mark.parametrize("size", [(20001, 1), (5000, 4001), (20000, 20000), (0, 10), (10, 0)])
def test_invalid_and_huge_dimensions_before_pixel_decode(tmp_path, monkeypatch, size):
    path = write_image(tmp_path)
    altered_png_size(path, *size)
    monkeypatch.setattr(PngImagePlugin.PngImageFile, "load", lambda self, *a, **k: pytest.fail("Unsafe pixel decode"))
    fails(path)


@pytest.mark.parametrize("size,pixels", [((5000, 4000), 20_000_000), ((20000, 1), 20000), ((1, 20000), 20000)])
def test_declared_dimension_ceilings_are_inclusive_without_allocating_pixels(size, pixels):
    image = SimpleNamespace(size=size, format="PNG", info={})
    image_input._dimensions(image, ImageInputSettings(max_decoded_pixels=pixels))
    with pytest.raises(ImageInputError) as error:
        image_input._dimensions(image, ImageInputSettings(max_decoded_pixels=pixels-1))
    assert error.value.code == "pixel_limit"


def test_configured_pixel_limit_before_decode(tmp_path, monkeypatch):
    path = write_image(tmp_path, size=(11, 10))
    monkeypatch.setattr(PngImagePlugin.PngImageFile, "load", lambda self, *a, **k: pytest.fail("Pixel cap bypassed"))
    fails(path, "pixel_limit", settings=ImageInputSettings(max_decoded_pixels=100))


def test_configured_output_limit_is_inclusive_and_never_truncates(tmp_path):
    path = write_image(tmp_path)
    size = len(preprocess_image(path).processed_bytes)
    assert preprocess_image(path, settings=ImageInputSettings(max_output_bytes=size))
    fails(path, "output_size_limit", settings=ImageInputSettings(max_output_bytes=size-1))


@pytest.mark.parametrize("orientation", [0, 9, 65535])
def test_invalid_exif_orientation_is_rejected(tmp_path, orientation):
    exif = Image.Exif()
    exif[274] = orientation
    fails(write_image(tmp_path, exif=exif), "invalid_metadata")


def test_no_payload_or_private_path_in_errors_or_logs(tmp_path, monkeypatch, caplog, capsys):
    path = write_image(tmp_path)
    def unsafe(*args, **kwargs):
        raise RuntimeError(f"PRIVATE_DECODER_DATA at {path}")
    monkeypatch.setattr(Image, "frombytes", unsafe)
    error = fails(path, "processing_failed")
    assert "PRIVATE" not in repr(error)
    assert not caplog.records
    assert capsys.readouterr() == ("", "")


def test_pillow_remains_optional_for_module_import(tmp_path, monkeypatch):
    path = write_image(tmp_path)
    original_import = builtins.__import__
    def missing(name, *args, **kwargs):
        if name == "PIL":
            raise ImportError("PRIVATE_PACKAGE_PATH")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", missing)
    fails(path, "dependency_unavailable")


@pytest.mark.parametrize("attribute,value", [("LOAD_TRUNCATED_IMAGES", True), ("MAX_IMAGE_PIXELS", None)])
def test_unsafe_process_decoder_settings_rejected_without_mutation(tmp_path, monkeypatch, attribute, value):
    path = write_image(tmp_path)
    target = ImageFile if attribute == "LOAD_TRUNCATED_IMAGES" else Image
    monkeypatch.setattr(target, attribute, value)
    fails(path, "unsafe_decoder_configuration")
    assert getattr(target, attribute) == value


def test_normal_processing_does_not_mutate_decoder_globals(tmp_path):
    before = (ImageFile.LOAD_TRUNCATED_IMAGES, Image.MAX_IMAGE_PIXELS)
    preprocess_image(write_image(tmp_path))
    assert before == (ImageFile.LOAD_TRUNCATED_IMAGES, Image.MAX_IMAGE_PIXELS)


def test_bomb_warning_safely_rejected(tmp_path, monkeypatch):
    path = write_image(tmp_path, size=(20, 10))
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 150)
    fails(path, "pixel_limit")
    assert Image.MAX_IMAGE_PIXELS == 150


def test_symlinks_and_junctions_rejected_before_read(tmp_path, monkeypatch):
    path = write_image(tmp_path)
    original = Path.lstat
    def reparse(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if self == path:
            return SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
        return result
    monkeypatch.setattr(Path, "lstat", reparse)
    fails(path, "invalid_path")


def test_original_file_opened_once_and_snapshot_used(tmp_path, monkeypatch):
    path = write_image(tmp_path)
    calls, original = [], os.open
    def tracked(name, *args, **kwargs):
        calls.append(name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(image_input.os, "open", tracked)
    preprocess_image(path)
    assert calls == [path]


def test_unknown_error_code_is_not_echoed():
    error = ImageInputError("PRIVATE_RAW_DATA")
    assert error.code == "processing_failed"
    assert "PRIVATE" not in repr(error)
