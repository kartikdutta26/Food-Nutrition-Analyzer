"""Stable M4 errors; input text, credentials and dependency errors are never echoed."""

MESSAGES = {
    "invalid_input": "Input does not match the recommendation contract.",
    "inconsistent_nutrition": "Nutrition, coverage or totals disagree with the supplied evidence.",
    "invalid_evidence": "Source or portion evidence is missing, invalid or inconsistent.",
    "stale_revision": "The expected session revision does not match the supplied session.",
    "input_limit": "Recommendation input exceeds the configured safety bounds.",
    "output_limit": "Complete recommendation output exceeds the configured safety bounds.",
    "invalid_rules": "The local interpretation rules are invalid.",
    "recommendation_failed": "Recommendations could not be produced safely.",
}


class RecommendationError(Exception):
    def __init__(self, code):
        self.code = code if code in MESSAGES else "recommendation_failed"
        super().__init__(MESSAGES[self.code])
