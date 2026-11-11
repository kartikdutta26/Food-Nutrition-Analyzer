# M5.2: safe local image preprocessing

This optional utility decodes a local photograph into bounded RGB PNG bytes. It
does **not** identify food, estimate portions, assign USDA IDs, derive nutrients,
call Ollama, upload files, or invoke M1/M3. A future recognizer must still return
unconfirmed food hypotheses and use the explicit M5.1 confirmation handoff.

## Install and run locally

Use the existing virtual environment, from the repository root:

```powershell
& agentic_ai/.venv/Scripts/python.exe -m pip install --only-binary=:all: -r agentic_ai/requirements-vision.txt
```

The isolated optional requirement is `Pillow==13.0.0`. Its CPython 3.14 Windows
AMD64 wheel was verified and installed in `agentic_ai/.venv` during development.
No M1-M4 requirements change. JPEG and zlib/PNG support are required. Importing
`agentic_ai.tools.image_input` itself does not import Pillow; preprocessing fails
with `dependency_unavailable` when the optional decoder cannot be imported.
Pillow is the only additional dependency. Package installation needs access to a
package index or a previously obtained compatible wheel; preprocessing and all
new tests run offline after installation.

```python
from io import BytesIO
from PIL import Image
from agentic_ai.tools.image_input import preprocess_image, ImageInputError

# Supply your own LOCAL path. Do not log that path or the returned bytes.
try:
    result = preprocess_image("my-local-photo.jpg", image_id="photo-a")
    # Metadata objects are existing M5.1 types; hashes bind the bytes actually read.
    assert result.image.original_sha256
    assert result.preprocessing.processed_sha256
    with Image.open(BytesIO(result.processed_bytes)) as preview:
        assert preview.mode == "RGB"
        assert max(preview.size) <= 1024
except ImageInputError as error:
    # Fixed code/message only. Do not include private caller context in logs.
    print(error.code)
```

No file is written by preprocessing. The source is read once into a bounded
snapshot; all verification, decoding and hashing use that same snapshot. The
return value contains `image: ImageReference`, `preprocessing:
PreprocessingMetadata`, `processed_bytes: bytes`, `processor_version=m5.2-v1`
and `decoder_version`. It is frozen, and its repr omits processed bytes. Do not
serialize the dataclass wholesale: use the metadata models' `model_dump` methods
when metadata is needed. Image hashes are content identifiers, not signatures,
authorization tokens, anonymization, or proof of recognition.

## Limits and preprocessing policy

`ImageInputSettings` is strict, frozen and rejects unknown fields. Each ceiling
can be lowered but cannot be exceeded. Pass a validated instance as `settings=`.

| Setting | Default / hard maximum | Behavior |
| --- | --- | --- |
| `max_input_bytes` | 10,485,760 (10 MiB) | Reject empty input and excess bytes, including file growth during bounded reading |
| `max_decoded_pixels` | 20,000,000 | Check header dimensions **before** pixel decoding; each original edge must also be 1-20,000 |
| `max_output_edge` | 1024 | Fit orientation-adjusted image, maintain aspect ratio and never upscale |
| `max_output_bytes` | 4,194,304 (4 MiB) | Bound encoding writes; return no truncated output |

Only regular local files with `.jpg`, `.jpeg`, or `.png` extensions (case
insensitive) and matching JPEG/PNG signatures and decoder formats are accepted.
URLs, UNC/network drives, device names, alternate data streams, symlinks and
Windows reparse points/junctions (including ancestors) are rejected. This is a
conservative local input API, not a file upload endpoint or a filesystem sandbox.
It does not authorize access to arbitrary paths on behalf of a remote user.

The utility verifies the container and strictly decodes it. Truncated files,
bad PNG checksums, trailing data after the expected end marker, animated PNG
(including one-frame APNG), and multi-picture MPO files are rejected. Decoding
warnings become sanitized failures. The utility refuses relaxed process-wide
Pillow truncated-image settings or a disabled decompression-bomb guard, and
never changes Pillow globals. Its own pixel limits apply independently.

EXIF orientation 1-8 is applied, including mirrored orientations. Original
dimensions remain pre-orientation; processed dimensions describe the transformed
pixels. Missing orientation means 1; malformed orientation is rejected. PNG
transparency and alpha are composited on **white**. Grayscale, palette, RGB and
CMYK are converted to RGB. Sixteen-bit integer PNG grayscale is scaled to eight
bits (divide by 257), rather than clipping most values to white. This stage does
not execute embedded profiles or perform color-managed ICC conversion; CMYK and
high-bit-depth conversion may lose color precision.

Resize uses Pillow LANCZOS. A fresh pixel-only RGB image is encoded to lossless
PNG with fixed compression level 9 and no optimization. No EXIF/GPS, ICC, XMP,
comments, text, timestamps or DPI are copied into the output. Only required PNG
IHDR/IDAT/IEND chunks remain. The exact original and processed SHA-256 hashes are
computed separately. Repeated processing is byte-deterministic with the same
settings, Pillow build and compression runtime. Cross-version/build byte
identity is not promised; `decoder_version` records the installed Pillow version.

## M5.1 compatibility boundary

The default 1024-edge policy produces metadata that validates inside the existing
full `ImageFoodRecognitionResult`, including rotated sources and rounded sizes.
Original `verification_scope=declared_metadata_only` is retained conservatively:
the M5.1 record still does not attest to model execution or food recognition.

A smaller configured edge produces a valid `PreprocessingMetadata` object, but
M5.1's full-result validator assumes the fixed 1024 fit size for large sources.
It rejects these smaller-policy full results. Use default settings when assembling
M5.1 recognition records. Supporting smaller edges throughout recognition needs
a separately reviewed policy/schema update; M5.2 does not change M5.1 contracts.
Preprocessing alone must never create a recognition result or invent model
provenance. No model has been run in this stage.

## Safe failures

`ImageInputError` has fixed public `code` and message text. Decoder exception
text, private paths, metadata and bytes are not logged, printed or exposed by
the utility. Unknown failures become `processing_failed` without chained
traceback display. Callers must also avoid logging arguments, exception locals,
payloads and private context.

| Code | Meaning |
| --- | --- |
| `invalid_settings`, `invalid_reference` | Invalid/reconstructed settings or image identifier |
| `invalid_path`, `unreadable_image` | Non-local/unsafe path, non-regular file, missing file or read failure |
| `unsupported_format` | Unsupported container, extension mismatch, or MPO |
| `input_size_limit`, `pixel_limit` | Empty/oversized bytes or invalid/excess decoded dimensions |
| `invalid_image`, `animated_image`, `invalid_metadata` | Failed verification/strict decode, animation, or invalid EXIF orientation |
| `output_size_limit` | Encoding would exceed the configured output byte cap |
| `dependency_unavailable`, `unsafe_decoder_configuration` | Missing optional decoder or relaxed global decoding settings |
| `processing_failed` | Other safe boundary failure, including resource/encoding errors |

Limits bound compressed bytes and decoded pixels, not native execution time or
absolute process memory. Pillow is native code and must be kept patched. This
is not malware detection, steganography removal, or a subprocess resource jail.
Visible private information remains in the pixels after metadata stripping.
An attacker able to modify local filesystem paths concurrently may race path
checks; treat the local filesystem and caller as trusted. A future remote upload
service needs controlled storage and process-level resource isolation.

## Deterministic validation

```powershell
$m52Temp = 'agentic_ai/.test-tmp-m52-' + [guid]::NewGuid().ToString('N')
& agentic_ai/.venv/Scripts/python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests/vision/test_image_input.py agentic_ai/tests/vision/test_image_input_security.py -q -rs --basetemp=$m52Temp
$m52FullTemp = 'agentic_ai/.test-tmp-m52-' + [guid]::NewGuid().ToString('N')
& agentic_ai/.venv/Scripts/python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests -q -rs --basetemp=$m52FullTemp
```

Fixtures are generated synthetic JPEG/PNG pixels and metadata, not real private
photographs. New tests block network connections via the existing vision-test
fixture. They cover format/extension validation, all eight EXIF orientations,
alpha/palette/grayscale/CMYK conversion, GPS/EXIF/XMP/ICC/text removal, deterministic
bytes/hashes, original immutability, M5.1 default-policy compatibility, animation,
corrupt/truncated containers, oversized headers before decoding, input/output
limits, unsafe paths, optional dependency failure, sanitized failures and
unchanged decoder globals. Existing live Ollama and USDA tests remain opt-in.

### Validation checkpoint

| Suite | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| New M5.2 image-input tests | 138 | 0 | 0 |
| Existing M1-M5.1 regression tests | 706 | 0 | 20 |
| Full combined suite | 844 | 0 | 20 |

The final full run took 25.27 seconds. Skips are the existing opt-in checks:
four live USDA and sixteen local Qwen3 checks. No model download, inference,
USDA request, database access or application service was needed for M5.2.
No test warnings were reported. `pip check` reported no broken requirements.
The compatible `pillow-13.0.0-cp314-cp314-win_amd64.whl` was installed only in the
ignored `agentic_ai/.venv`, using an explicit public package index, binary-only
installation, no cache and no dependency installation.

Preservation audit: all 260 pre-existing tracked/untracked source files matched
their starting SHA-256 fingerprints, including the two locally modified ignore
files and 73 untracked `local_preview` files. Existing M1-M5.1 code, requirements,
contracts and tests were not edited. Only the five M5.2 source/test/requirement/
documentation files are new; all remain uncommitted.
