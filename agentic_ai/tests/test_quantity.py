import pytest

from agentic_ai.schemas.quantity import parse_quantity


@pytest.mark.parametrize(("text", "expected"), [
    ("1.5", 1.5), (".5", .5), ("1/2", .5), ("3 / 4", .75),
    ("1 1/2", 1.5), ("2 3/4", 2.75), ("\u00bd", .5), ("1\u00bd", 1.5),
    ("\u2153", 1/3), ("1\u20442", .5), ("two", 2), ("TWENTY-ONE", 21),
    ("half", .5), ("half a", .5), ("a quarter", .25), ("three quarters", .75),
    ("one and a half", 1.5), ("two and one quarter", 2.25), ("an", 1),
    ("1,250", 1250), ("1,250.5", 1250.5), ("0", 0), ("-2", -2),
    ("-1 1/2", -1.5), ("-0 1/2", -.5), ("\u22122", -2),
])
def test_explicit_quantities(text, expected):
    assert parse_quantity(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", [
    "some", "a few", "2-3", "2 to 3", "about two", "1/0", "NaN", "inf",
    "1,5", "", "twenty twenty", "one and two", "two eggs", "1e3",
])
def test_ambiguous_or_unsupported_quantities_are_unknown(text):
    assert parse_quantity(text) is None


def test_unrepresentable_fraction_does_not_crash():
    assert parse_quantity("9" * 1000 + "/1") is None
