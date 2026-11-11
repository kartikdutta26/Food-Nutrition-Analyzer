"""M4 CLI: interpret existing M2/M3 JSON or labelled offline USDA examples.

No Qwen ranking, inference, live USDA, backend or database connection is performed.
Only the demo fixture builder invokes M2 with the authentic local USDA snapshot.
"""
import argparse
import json
import sys
from pathlib import Path

from agentic_ai.agents.recommendation_agent import NutritionRecommendationAgent
from agentic_ai.recommendation_errors import RecommendationError
from agentic_ai.recommendation.validation import strict_json


def _read(path, limit):
    try:
        with path.open("rb") as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise RecommendationError("input_limit")
        return strict_json(raw)
    except RecommendationError:
        raise
    except (OSError, ValueError):
        raise RecommendationError("invalid_input") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline-examples", action="store_true")
    mode.add_argument("--input-json", type=Path)
    parser.add_argument("--kind", choices=["nutrition", "session", "request"], default="nutrition")
    parser.add_argument("--context-json", type=Path)
    parser.add_argument("--expected-revision", type=int)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    agent = NutritionRecommendationAgent()
    try:
        if args.offline_examples:
            if args.context_json or args.expected_revision is not None or args.kind != "nutrition":
                raise RecommendationError("invalid_input")
            # Imported only for explicitly requested fixture generation, not by M4.
            from agentic_ai.agents.nutrition_agent import NutritionAnalysisAgent
            from agentic_ai.providers.usda import SnapshotProvider
            from agentic_ai.schemas.food import FoodUnderstandingResult
            examples = _read(Path(__file__).parent / "data/demo_extractions.json", agent.settings.max_input_bytes)
            source = NutritionAnalysisAgent(SnapshotProvider())
            for index, example in enumerate(examples):
                nutrition = source.analyze(FoodUnderstandingResult.model_validate(example["extraction"]))
                output = agent.recommend(nutrition)
                print(json.dumps({"example":index + 1,
                    "extraction_mode":"existing curated fixtures; no model inference",
                    "nutrition_provider":"authentic committed USDA snapshot; no live USDA request",
                    "recommendation_mode":"deterministic composition interpretation; no Qwen ranking",
                    "result":output.model_dump(mode="json")}, ensure_ascii=True), flush=True)
            return 0
        payload = _read(args.input_json, agent.settings.max_input_bytes)
        if args.kind == "request":
            if args.context_json or args.expected_revision is not None:
                raise RecommendationError("invalid_input")
            result = agent.recommend_request(payload)
        else:
            context = _read(args.context_json, 65536) if args.context_json else None
            if args.kind == "session":
                result = agent.recommend_session(payload, context=context, expected_revision=args.expected_revision)
            else:
                if args.expected_revision is not None:
                    raise RecommendationError("invalid_input")
                result = agent.recommend(payload, context=context)
        print(result.model_dump_json())
        return 0
    except RecommendationError as error:
        print(json.dumps({"status":"error", "error":{"code":error.code,"message":str(error)}}))
        return 1
    except Exception:
        print(json.dumps({"status":"error", "error":{"code":"recommendation_failed","message":"The input could not be interpreted safely."}}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
