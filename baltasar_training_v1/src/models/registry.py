"""Model registry for easy future extension."""

from __future__ import annotations

from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier


MODEL_REGISTRY = {
    "DecisionTreeClassifier": DecisionTreeClassifier,
    "RandomForestClassifier": RandomForestClassifier,
    "HistGradientBoostingClassifier": HistGradientBoostingClassifier,
}


def build_model(class_name: str, params: dict):
    """Instantiate a configured sklearn model."""
    if class_name not in MODEL_REGISTRY:
        raise KeyError(
            f"Unknown model class {class_name!r}. Register it in MODEL_REGISTRY to extend the lab."
        )
    return MODEL_REGISTRY[class_name](**params)
