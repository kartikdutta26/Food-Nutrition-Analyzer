"""Milestone 2 CLI. --examples uses real Qwen3; --offline-examples uses labeled inputs."""

import argparse
import json
import sys
import time
from pathlib import Path

from pydantic import ValidationError

from agentic_ai.agents.food_agent import FoodUnderstandingAgent
from agentic_ai.agents.nutrition_agent import NutritionAnalysisAgent
from agentic_ai.errors import FoodUnderstandingError
from agentic_ai.nutrition_errors import NutritionError, NutritionInputError
from agentic_ai.providers.usda import LiveUSDAProvider, SnapshotProvider
from agentic_ai.schemas.food import FoodUnderstandingResult
from agentic_ai.schemas.nutrition import ItemSelection

EXAMPLES = [
    "I ate 100 g boiled eggs and 150 g cooked white rice.",
    "I ate 2 small rotis and 1/2 cup cooked white rice.",
    "I ate 1 medium banana.",
    "I drank 250 ml whole milk.",
    "I ate 100 g bananas and one bowl of paneer curry.",
    "I ate 100 g apples.",
]


def parse_selections(select, grams):
    values = {}
    try:
        for value in select:
            parts = value.split(":")
            if len(parts) not in {2, 3}:
                raise ValueError()
            index = int(parts[0])
            if index in values:
                raise ValueError()
            values[index] = {"item_index": index, "fdc_id": int(parts[1])}
            if len(parts) == 3:
                values[index]["portion_id"] = parts[2]
        for value in grams:
            index, amount = value.split(":")
            index = int(index)
            if "measured_grams" in values.get(index, {}):
                raise ValueError()
            values.setdefault(index, {"item_index": index})["measured_grams"] = amount
        return [ItemSelection(**value) for value in values.values()]
    except (ValueError, ValidationError):
        raise NutritionInputError("Use --select INDEX:FDC_ID[:PORTION_ID] and --grams INDEX:TOTAL_EDIBLE_GRAMS; indices start at zero.") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description="USDA nutrition calculations with explicit source and portion evidence.")
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--text")
    inputs.add_argument("--examples", action="store_true", help="Run six descriptions through actual local Qwen3, then nutrition tools.")
    inputs.add_argument("--offline-examples", action="store_true", help="Use curated extraction fixtures; no Qwen3 or network calls.")
    inputs.add_argument("--input-json", type=Path, help="A Milestone 1 FoodUnderstandingResult JSON file.")
    parser.add_argument("--provider", choices=["snapshot", "live"], default="snapshot")
    parser.add_argument("--select", action="append", default=[], metavar="INDEX:FDC_ID[:PORTION_ID]")
    parser.add_argument("--grams", action="append", default=[], metavar="INDEX:TOTAL_EDIBLE_GRAMS")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        selections = parse_selections(args.select, args.grams)
        if selections and (args.examples or args.offline_examples):
            raise NutritionInputError("Use selections with one --text or --input-json request.")
        provider = SnapshotProvider() if args.provider == "snapshot" else LiveUSDAProvider()
        nutrition_agent = NutritionAnalysisAgent(provider)
        if args.offline_examples:
            jobs = json.loads((Path(__file__).parent / "data" / "demo_extractions.json").read_text(encoding="utf-8"))
            extraction_mode = "curated extraction fixtures; no model inference"
        elif args.input_json:
            jobs = [{"text": None, "extraction": json.loads(args.input_json.read_text(encoding="utf-8"))}]
            extraction_mode = "supplied Milestone 1 extraction JSON; no model inference"
        else:
            jobs = [{"text": text} for text in EXAMPLES] if args.examples else [{"text": args.text}]
            extraction_mode = "actual local Ollama inference"
        food_agent = FoodUnderstandingAgent() if extraction_mode == "actual local Ollama inference" else None
    except (NutritionError, FoodUnderstandingError, OSError, ValueError) as error:
        print(json.dumps({"status": "error", "error": {"code": getattr(error, "code", "invalid_input_file"), "message": str(error) if isinstance(error, (NutritionError, FoodUnderstandingError)) else "Could not read the input JSON file."}}))
        return 1
    failed = False
    for job in jobs:
        start = time.monotonic()
        try:
            extraction = food_agent.analyze(job["text"]) if food_agent else FoodUnderstandingResult.model_validate(job["extraction"])
            result = nutrition_agent.analyze(extraction, selections)
            output = {"input": job["text"], "extraction_mode": extraction_mode, "nutrition_provider": args.provider, "food_understanding": extraction.model_dump(mode="json"), "nutrition": result.model_dump(mode="json")}
            failed |= result.status == "error" or any(item.status == "error" for item in result.items)
        except (NutritionError, FoodUnderstandingError, ValidationError) as error:
            failed = True
            output = {"input": job["text"], "status": "error", "error": {"code": getattr(error, "code", "invalid_extraction"), "message": str(error) if isinstance(error, (NutritionError, FoodUnderstandingError)) else "Input does not match the Milestone 1 contract."}}
        output["elapsed_seconds"] = round(time.monotonic() - start, 2)
        print(json.dumps(output, ensure_ascii=False), flush=True)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
