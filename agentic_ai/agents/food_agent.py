
import re


def recognize_food(text):
    """
    Initial prototype for extracting food names and quantities.
    This is rule-based; we will add an LLM in the next phase.
    """
    known_foods = ["egg", "banana", "apple", "milk", "rice"]

    results = []

    for food in known_foods:
        pattern = rf"\b(\d+)\s+{food}s?\b"
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            results.append({
                "food": food,
                "quantity": int(match.group(1))
            })

    return results


if __name__ == "__main__":
    user_input = "I ate 2 eggs and 1 banana"
    print(recognize_food(user_input))
