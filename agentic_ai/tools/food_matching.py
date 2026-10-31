"""Conservative lexical matching; no nutrient values or LLM scoring are used."""

import re

from agentic_ai.schemas.nutrition import FoodCandidate

ALIASES = {"eggs": "egg", "bananas": "banana", "apples": "apple", "rotis": "roti", "chapati": "roti", "chapatis": "roti", "chapatti": "roti", "chappatti": "roti", "chappatis": "roti", "uncooked": "raw", "steaming": "steamed", "boiling": "boiled", "frying": "fried", "grilling": "grilled"}
COOKING = {"boiled", "fried", "grilled", "roasted", "steamed", "baked", "scrambled", "poached", "omelet"}
SPECIAL = {"powder", "dehydrated", "dried", "juice", "flour", "chips", "chip", "extract", "concentrate", "cake", "pie", "pudding", "sauce", "cereal", "bar", "pepper", "formula", "baby", "flavor", "flavored"}
QUALIFIERS = {"brown", "white", "basmati", "jasmine", "whole", "skim", "nonfat", "lowfat", "reducedfat", "sweetened", "unsweetened", "salted", "unsalted"}
INGREDIENTS = {"chicken", "beef", "pork", "fish", "egg", "rice", "cheese", "paneer", "milk", "nuts", "sugar", "oil", "butter"}


def tokens(text):
    value = text.casefold().replace("low-fat", "lowfat").replace("low fat", "lowfat").replace("reduced-fat", "reducedfat")
    return {ALIASES.get(token, token) for token in re.findall(r"[a-z]+|\d+(?:\.\d+)?", value)}


def search_query(food):
    name = food.name.casefold()
    for original, replacement in ALIASES.items():
        name = re.sub(rf"\b{re.escape(original)}\b", replacement, name)
    if food.preparation and food.preparation.casefold() not in name:
        name += " " + food.preparation.casefold()
    return name


def _skin(text):
    if re.search(r"\bwithout skin\b|\bpeeled\b|\bskinless\b", text.casefold()):
        return "without"
    if re.search(r"\bwith skin\b|\bunpeeled\b", text.casefold()):
        return "with"
    return None


def compatible(food, candidate: FoodCandidate):
    requested = tokens(" ".join([food.name, food.preparation or "", food.source_text]))
    identity = tokens(food.name) - {"food", "unknown", "small", "medium", "large", "extra", "sliced", "chopped", "mashed", "quartered"}
    actual = tokens(candidate.description)
    if not identity or not identity <= actual:
        return False
    if (SPECIAL & actual) - requested:
        return False
    if (INGREDIENTS & actual) - requested:
        return False
    if (QUALIFIERS & requested) - actual:
        return False
    requested_method = requested & COOKING
    actual_method = actual & COOKING
    if requested_method and not requested_method <= actual_method:
        return False
    if requested_method and (actual_method - requested_method):
        return False
    if "raw" in requested and ("cooked" in actual or actual_method):
        return False
    if ("cooked" in requested or requested_method) and "raw" in actual:
        return False
    skin = _skin(food.source_text)
    if skin and _skin(candidate.description) != skin:
        return False
    def fortification(text):
        if re.search(r"\bwithout (?:added )?vitamin", text, re.I):
            return False
        if re.search(r"\bwith (?:added )?vitamin", text, re.I):
            return True
        return None
    fortified = fortification(food.source_text)
    if fortified is not None and fortification(candidate.description) != fortified:
        return False
    # Percent fat, if explicitly stated, must appear in the database description.
    percent = re.search(r"\b(\d+(?:\.\d+)?)\s*%", food.source_text)
    if percent and not re.search(rf"\b{re.escape(percent[1])}\s*%", candidate.description):
        return False
    return True


def preparation_needed(food, candidate):
    stated = tokens(" ".join([food.name, food.preparation or "", food.source_text]))
    actual = tokens(candidate.description)
    return bool((actual & COOKING or "cooked" in actual) and not (stated & (COOKING | {"cooked", "raw"})))
