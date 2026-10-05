"""
Score classifier — map numeric score → Classification enum.

Thresholds:
  90-100: Excellent 🟢 (best practice level)
  75-89:  Good      🔵 (production ready)
  60-74:  Fair      🟡 (needs improvement)
  <60:    Poor      🔴 (high risk)
"""

from app.models.score import Classification


CLASSIFICATION_THRESHOLDS = [
    (90.0, Classification.EXCELLENT),
    (75.0, Classification.GOOD),
    (60.0, Classification.FAIR),
]


def classify_score(score: float) -> Classification:
    """
    Phân loại score thành Classification enum.

    Args:
        score: Numeric score 0.0–100.0

    Returns:
        Classification enum value
    """
    for threshold, classification in CLASSIFICATION_THRESHOLDS:
        if score >= threshold:
            return classification
    return Classification.POOR


def get_classification_emoji(classification: Classification) -> str:
    """Trả về emoji cho classification (dùng trong UI/logs)."""
    emojis = {
        Classification.EXCELLENT: "🟢",
        Classification.GOOD: "🔵",
        Classification.FAIR: "🟡",
        Classification.POOR: "🔴",
    }
    return emojis.get(classification, "⚪")
