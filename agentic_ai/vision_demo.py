"""Local readiness/recognition CLI. Never downloads a model or invokes M3."""
import argparse
from dataclasses import asdict
import json
import os
import sys

from agentic_ai.agents.image_food_agent import ImageFoodRecognitionAgent
from agentic_ai.clients.ollama_vision_client import OllamaVisionClient
from agentic_ai.tools.image_input import ImageInputError
from agentic_ai.vision_runtime_config import VisionRuntimeSettings
from agentic_ai.vision_runtime_errors import VisionRuntimeError


def available_ram_bytes():
    """Read only available physical RAM; no process enumeration/termination."""
    try:
        if os.name == "nt":
            import ctypes
            class MemoryStatus(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                    (name, ctypes.c_ulonglong) for name in ("total", "available", "total_page",
                                                           "available_page", "total_virtual", "available_virtual", "extended")]
            status = MemoryStatus()
            status.length = ctypes.sizeof(status)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                raise OSError()
            return int(status.available)
        return os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    except Exception:
        raise VisionRuntimeError("memory_unavailable") from None


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise VisionRuntimeError("invalid_configuration")


def main(argv=None):
    try:
        parser = _SafeParser(description="Check local Qwen3-VL readiness, or propose unconfirmed food identities.")
        parser.add_argument("--image", help="Local JPEG/PNG path; never logged or included in output")
        parser.add_argument("--base-url", default="http://127.0.0.1:11434", help="Numeric loopback HTTP origin only")
        parser.add_argument("--check", action="store_true", help="Read metadata only, without model inference (default)")
        args = parser.parse_args(argv)
        if args.check and args.image:
            raise VisionRuntimeError("invalid_configuration")
        try:
            settings = VisionRuntimeSettings(base_url=args.base_url)
        except ValueError:
            raise VisionRuntimeError("invalid_configuration") from None
        available = available_ram_bytes()
        print(json.dumps({"available_ram_gib": round(available / 2**30, 2),
                          "demo_minimum_available_gib": 4}), file=sys.stderr)
        client = OllamaVisionClient(settings)
        selected = client.check_ready()
        if args.image is None:
            print(json.dumps({"model_installed_and_vision_capable": True, "inference_tested": False,
                              "model": asdict(selected)}, sort_keys=True))
            return 0
        # Conservative demo guard, not a measured guarantee of model requirements.
        if available < 4 * 2**30:
            raise VisionRuntimeError("insufficient_memory")
        result = ImageFoodRecognitionAgent(settings=settings, client=client).analyze(args.image)
        print(result.model_dump_json(indent=2, ensure_ascii=True))
        return 0
    except (VisionRuntimeError, ImageInputError) as error:
        print(json.dumps({"error": error.code}), file=sys.stderr)
        return 2
    except Exception:
        print(json.dumps({"error": "inference_failed"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
