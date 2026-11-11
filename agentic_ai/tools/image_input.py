"""Bounded, local-only JPEG/PNG preprocessing. No recognition or transport.

Pillow is optional and imported on use. Public failures contain fixed codes only.
Input paths and image bytes are never logged or included in result reprs.
"""
from dataclasses import dataclass, field
import hashlib
from io import BytesIO
import os
from pathlib import Path
import stat
import warnings
import zlib

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from agentic_ai.schemas.vision import ImageReference, PreprocessingMetadata


_MESSAGES = {
    "invalid_settings": "Image input settings are invalid.",
    "invalid_reference": "Image reference identifier is invalid.",
    "invalid_path": "A regular local image file is required.",
    "unreadable_image": "The local image could not be read.",
    "unsupported_format": "Only matching JPEG and PNG files are accepted.",
    "input_size_limit": "Image input exceeds the byte limit or is empty.",
    "pixel_limit": "Image dimensions exceed the configured limits.",
    "invalid_image": "Image data is corrupt, incomplete or invalid.",
    "animated_image": "Animated or multi-frame images are not accepted.",
    "invalid_metadata": "Image orientation metadata is invalid.",
    "output_size_limit": "Processed image exceeds the output byte limit.",
    "dependency_unavailable": "The optional Pillow decoder is unavailable.",
    "unsafe_decoder_configuration": "Strict image decoding is required.",
    "processing_failed": "Image processing could not be completed safely.",
}


class ImageInputError(ValueError):
    """Safe boundary error; never includes a path, bytes or decoder message."""

    def __init__(self, code):
        self.code = code if code in _MESSAGES else "processing_failed"
        super().__init__(_MESSAGES[self.code])


class ImageInputSettings(BaseModel):
    """Limits can be lowered, never raised above the M5.2 safety ceilings."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid",
                             revalidate_instances="always", hide_input_in_errors=True)
    max_input_bytes: int = Field(default=10_485_760, ge=1, le=10_485_760)
    max_decoded_pixels: int = Field(default=20_000_000, ge=1, le=20_000_000)
    max_output_edge: int = Field(default=1024, ge=1, le=1024)
    max_output_bytes: int = Field(default=4_194_304, ge=1, le=4_194_304)


@dataclass(frozen=True, slots=True)
class ProcessedImage:
    """Only processed pixels leave the utility; no original path or raw input."""

    image: ImageReference
    preprocessing: PreprocessingMetadata
    processed_bytes: bytes = field(repr=False)
    processor_version: str = "m5.2-v1"
    decoder_version: str = ""


class _BoundedOutput(BytesIO):
    def __init__(self, limit):
        super().__init__()
        self.limit = limit

    def write(self, data):
        if self.tell() + len(data) > self.limit:
            raise ImageInputError("output_size_limit")
        return super().write(data)


def _pillow():
    try:
        from PIL import Image, ImageFile, ImageOps, __version__
    except ImportError:
        raise ImageInputError("dependency_unavailable") from None
    # Do not change process-wide decoder settings used by other modules.
    if ImageFile.LOAD_TRUNCATED_IMAGES or Image.MAX_IMAGE_PIXELS is None:
        raise ImageInputError("unsafe_decoder_configuration")
    return Image, ImageOps, __version__


def _local_path(value):
    if not isinstance(value, (str, Path)):
        raise ImageInputError("invalid_path")
    text = str(value)
    if (not text or len(text) > 4096 or "\x00" in text
            or text.startswith(("\\\\", "//")) or "://" in text):
        raise ImageInputError("invalid_path")
    path = Path(text)
    # Block URLs, alternate data streams and Windows device names on all hosts.
    tail = text[2:] if len(text) >= 2 and text[0].isalpha() and text[1] == ":" else text
    if ":" in tail:
        raise ImageInputError("invalid_path")
    reserved = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    reserved.update(f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(10))
    if any(part.rstrip(" .").split(".")[0].upper() in reserved
           or (part not in {".", ".."} and part.endswith((" ", ".")))
           for part in path.parts if part != path.anchor):
        raise ImageInputError("invalid_path")
    try:
        # Refuse symlinks/junctions, including ancestors, before resolving.
        absolute = Path(os.path.abspath(path))
        for component in (absolute, *absolute.parents):
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ImageInputError("invalid_path")
        if os.name == "nt":
            import ctypes
            # Mapped network drives are not local input either.
            if ctypes.windll.kernel32.GetDriveTypeW(absolute.anchor) not in {2, 3, 5, 6}:
                raise ImageInputError("invalid_path")
    except ImageInputError:
        raise
    except (OSError, ValueError):
        raise ImageInputError("unreadable_image") from None
    return absolute


def _read_image(path, limit):
    suffix = path.suffix.lower()
    expected = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG"}.get(suffix)
    if expected is None:
        raise ImageInputError("unsupported_format")
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
        with os.fdopen(os.open(path, flags), "rb") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ImageInputError("invalid_path")
            if not 0 < info.st_size <= limit:
                raise ImageInputError("input_size_limit")
            data = source.read(limit + 1)
        if not 0 < len(data) <= limit:
            raise ImageInputError("input_size_limit")
    except ImageInputError:
        raise
    except OSError:
        raise ImageInputError("unreadable_image") from None
    detected = "PNG" if data.startswith(b"\x89PNG\r\n\x1a\n") else "JPEG" if data.startswith(b"\xff\xd8\xff") else None
    if detected != expected:
        raise ImageInputError("unsupported_format")
    if ((detected == "JPEG" and not data.endswith(b"\xff\xd9"))
            or (detected == "PNG" and not data.endswith(b"\x00\x00\x00\x00IEND\xaeB`\x82"))):
        raise ImageInputError("invalid_image")
    return data, expected


def _dimensions(image, settings):
    width, height = image.size
    if (not 0 < width <= 20_000 or not 0 < height <= 20_000
            or width * height > settings.max_decoded_pixels):
        raise ImageInputError("pixel_limit")
    if image.format not in {"JPEG", "PNG"}:
        raise ImageInputError("unsupported_format")
    if getattr(image, "is_animated", False) or getattr(image, "n_frames", 1) != 1 or "loop" in image.info:
        raise ImageInputError("animated_image")


def _orientation(image):
    value = image.getexif().get(274, 1)
    if type(value) is not int or not 1 <= value <= 8:
        raise ImageInputError("invalid_metadata")
    return value


def _container_end(data, format):
    """Check bounded framing too: decoder verify may ignore trailing payloads."""
    if format == "PNG":
        offset = 8
        while offset + 12 <= len(data):
            length = int.from_bytes(data[offset:offset+4], "big")
            kind = data[offset+4:offset+8]
            end = offset + 12 + length
            if end > len(data) or (kind == b"IHDR" and offset != 8):
                break
            if zlib.crc32(data[offset+4:end-4]) != int.from_bytes(data[end-4:end], "big"):
                break
            if kind in {b"acTL", b"fcTL", b"fdAT"}:
                raise ImageInputError("animated_image")
            if kind == b"IEND":
                if length == 0 and end == len(data):
                    return
                break
            offset = end
    else:
        # JPEG segment lengths skip arbitrary EXIF/comment bytes. In entropy
        # scans FF00 escapes and restart markers are not end-of-image markers.
        offset, in_scan = 2, False
        while offset < len(data):
            if in_scan:
                offset = data.find(b"\xff", offset)
                if offset < 0:
                    break
            if data[offset] != 255:
                break
            while offset < len(data) and data[offset] == 255:
                offset += 1
            if offset >= len(data):
                break
            marker = data[offset]
            offset += 1
            if in_scan and (marker == 0 or 0xD0 <= marker <= 0xD7):
                continue
            continuing_scan = in_scan and marker == 0xDC
            in_scan = False
            if marker == 0xD9:
                if offset == len(data):
                    return
                break
            if marker in {0, 0xD8} or 0xD0 <= marker <= 0xD7:
                break
            if marker == 1:  # TEM, standalone marker.
                continue
            if offset + 2 > len(data):
                break
            length = int.from_bytes(data[offset:offset+2], "big")
            if length < 2 or offset + length > len(data):
                break
            offset += length
            in_scan = marker == 0xDA or continuing_scan
    raise ImageInputError("invalid_image")


def _decode(data, settings, Image, ImageOps):
    # Verify container checksums first, then decode the same bounded snapshot.
    # Strict load catches truncated JPEG data that JPEG.verify alone cannot.
    with Image.open(BytesIO(data), formats=("JPEG", "PNG")) as checked:
        _dimensions(checked, settings)
        original_size = checked.size
        _container_end(data, checked.format)
        checked.verify()
    with Image.open(BytesIO(data), formats=("JPEG", "PNG")) as decoded:
        _dimensions(decoded, settings)
        decoded.load()
        orientation = _orientation(decoded)
        normalized = ImageOps.exif_transpose(decoded)
        try:
            # Explicit white alpha background; never silently discard alpha.
            if normalized.mode in {"RGBA", "LA", "P"} or "transparency" in normalized.info:
                with normalized.convert("RGBA") as rgba:
                    rgb = Image.new("RGB", rgba.size, "white")
                    rgb.paste(rgba, mask=rgba.getchannel("A"))
            elif normalized.mode in {"I;16", "I;16B", "I;16L", "I"}:
                # PNG integer grayscale is 16-bit; scale rather than clip to 255.
                with normalized.convert("F") as floating:
                    with floating.point(lambda value: value / 257) as scaled:
                        with scaled.convert("L") as gray:
                            rgb = gray.convert("RGB")
            else:
                rgb = normalized.convert("RGB")
        finally:
            normalized.close()
    return rgb, original_size, orientation


def preprocess_image(path, *, image_id=None, settings=None):
    """Read a regular local JPEG/PNG, return metadata and deterministic RGB PNG.

    Default output fits unchanged M5.1 result contracts. Smaller configured edges
    produce valid PreprocessingMetadata, but M5.1's full-result validator assumes
    the fixed 1024 fit policy; do not assemble such results without a policy update.
    Errors are sanitized; callers must not log paths or processed_bytes either.
    """
    try:
        if settings is None:
            settings = ImageInputSettings()
        elif not isinstance(settings, ImageInputSettings):
            raise ImageInputError("invalid_settings")
        else:
            try:
                settings = ImageInputSettings.model_validate(settings)
            except ValidationError:
                raise ImageInputError("invalid_settings") from None
        if image_id is not None:
            # Validate before opening private data; no coercion or raw value errors.
            try:
                ImageReference(image_id=image_id, original_sha256="0"*64,
                               media_type="image/png", byte_size=1, width=1, height=1)
            except ValidationError:
                raise ImageInputError("invalid_reference") from None
        local = _local_path(path)
        data, source_format = _read_image(local, settings.max_input_bytes)
        original_hash = hashlib.sha256(data).hexdigest()
        Image, ImageOps, version = _pillow()
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            try:
                rgb, original_size, orientation = _decode(data, settings, Image, ImageOps)
            except Image.DecompressionBombError:
                raise ImageInputError("pixel_limit") from None
            except Image.DecompressionBombWarning:
                raise ImageInputError("pixel_limit") from None
            except ImageInputError:
                raise
            except (OSError, ValueError, SyntaxError, Warning, OverflowError):
                raise ImageInputError("invalid_image") from None
            try:
                rgb.thumbnail((settings.max_output_edge, settings.max_output_edge), Image.Resampling.LANCZOS)
                # Fresh pixel-only image prevents save() from inheriting ANY metadata.
                with Image.frombytes("RGB", rgb.size, rgb.tobytes()) as clean:
                    with _BoundedOutput(settings.max_output_bytes) as output:
                        clean.save(output, format="PNG", optimize=False, compress_level=9)
                        processed_bytes = output.getvalue()
                    processed_size = clean.size
            finally:
                rgb.close()
        image = ImageReference(image_id=image_id or "img-"+original_hash[:24],
                               original_sha256=original_hash,
                               media_type="image/jpeg" if source_format == "JPEG" else "image/png",
                               byte_size=len(data), width=original_size[0], height=original_size[1])
        metadata = PreprocessingMetadata(processed_sha256=hashlib.sha256(processed_bytes).hexdigest(),
                                         media_type="image/png", width=processed_size[0], height=processed_size[1],
                                         original_exif_orientation=orientation, metadata_removed=True)
        return ProcessedImage(image, metadata, processed_bytes, decoder_version=version)
    except ImageInputError:
        raise
    except Exception:
        # Decoder details may contain private metadata. No chaining or logging.
        raise ImageInputError("processing_failed") from None
