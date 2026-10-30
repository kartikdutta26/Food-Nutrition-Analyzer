"""Run from the repository root: python -m agentic_ai.demo --examples."""

import argparse
import json
import sys
import time

from agentic_ai.agents.food_agent import FoodUnderstandingAgent
from agentic_ai.errors import FoodUnderstandingError


EXAMPLES = [
    "For lunch I ate 2 rotis, 1/2 cup dal tadka and 150 g cooked rice.",
    "I had one masala dosa and half a cup of sambar.",
    "Breakfast was 2 boiled eggs, 1.5 bananas and 250 ml milk.",
    "Dinner was 120 g grilled chicken and one and a half cups of steamed broccoli.",
    "I ate paneer curry and some rice.",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NutriAI local food understanding; no nutrition estimates.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--text", help="One meal description, quoted as a single argument.")
    mode.add_argument("--examples", action="store_true", help="Run Indian and international examples.")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        agent = FoodUnderstandingAgent()
    except FoodUnderstandingError as exc:
        print(json.dumps({"status": "error", "error": {"code": exc.code, "message": str(exc)}}))
        return 1
    failed = False
    for text in EXAMPLES if args.examples else [args.text]:
        start = time.monotonic()
        try:
            result = agent.analyze(text)
            output = {"input": text, "model": agent.settings.model, "result": result.model_dump()}
        except FoodUnderstandingError as exc:
            failed = True
            output = {"input": text, "status": "error", "error": {"code": exc.code, "message": str(exc)}}
        output["elapsed_seconds"] = round(time.monotonic() - start, 2)
        print(json.dumps(output, ensure_ascii=False, indent=2), flush=True)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
