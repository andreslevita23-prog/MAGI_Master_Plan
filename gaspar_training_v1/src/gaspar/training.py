from __future__ import annotations

import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import ConfusionMatrixDisplay, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

from .data import load_dataset
from .features import (
    build_feature_frame,
    categorical_features_for_target,
    feature_columns_for_target,
    numeric_features_for_target,
)
from .targeting import attach_heuristic_target


def temporal_split(data: pd.DataFrame, train_ratio: float = 0.70) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = data.copy()
    if "timestamp" in ordered.columns:
        ordered["timestamp_sort"] = pd.to_datetime(ordered["timestamp"], errors="coerce")
        ordered = ordered.sort_values(["timestamp_sort", "source_file"], na_position="last")
    split_at = max(1, int(len(ordered) * train_ratio))
    return ordered.iloc[:split_at].copy(), ordered.iloc[split_at:].copy()


def build_model(target_version: str = "v1") -> Pipeline:
    numeric_features = numeric_features_for_target(target_version)
    categorical_features = categorical_features_for_target(target_version)
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", SimpleImputer(strategy="median"), numeric_features),
            ("cat", Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore")),
            ]), categorical_features),
        ]
    )
    classifier = DecisionTreeClassifier(max_depth=5, min_samples_leaf=20, random_state=42)
    return Pipeline([("features", preprocessor), ("model", classifier)])


def feature_importance(model: Pipeline) -> list[dict[str, float | str]]:
    classifier = model.named_steps["model"]
    if not hasattr(classifier, "feature_importances_"):
        return []

    try:
        feature_names = model.named_steps["features"].get_feature_names_out()
    except Exception:
        feature_names = feature_columns_for_target()

    rows = [
        {"feature": str(name), "importance": float(importance)}
        for name, importance in zip(feature_names, classifier.feature_importances_)
    ]
    rows.sort(key=lambda item: item["importance"], reverse=True)
    return rows


def walk_forward_evaluation(data: pd.DataFrame, folds: int = 4, target_version: str = "v1") -> pd.DataFrame:
    if len(data) < 12:
        return pd.DataFrame(columns=["fold", "train_rows", "test_rows", "f1_macro"])

    ordered = data.copy().reset_index(drop=True)
    fold_size = max(1, len(ordered) // (folds + 1))
    rows = []
    for fold in range(1, folds + 1):
        train_end = fold_size * fold
        test_end = min(len(ordered), train_end + fold_size)
        if test_end <= train_end:
            continue
        train = ordered.iloc[:train_end]
        test = ordered.iloc[train_end:test_end]
        if train["voto"].nunique() < 2 or test["voto"].nunique() < 1:
            continue
        model = build_model(target_version)
        model.fit(build_feature_frame(train, target_version=target_version), train["voto"])
        prediction = model.predict(build_feature_frame(test, target_version=target_version))
        rows.append({
            "fold": fold,
            "train_rows": len(train),
            "test_rows": len(test),
            "f1_macro": f1_score(test["voto"], prediction, average="macro", zero_division=0),
        })
    return pd.DataFrame(rows)


def plot_class_distribution(data: pd.DataFrame, output_path: Path) -> None:
    counts = data["voto"].value_counts().reindex(["GOOD", "FAIR", "POOR"]).fillna(0)
    fig, ax = plt.subplots(figsize=(6, 4))
    counts.plot(kind="bar", ax=ax, color=["#2d7d46", "#c5902e", "#9f3b3b"])
    ax.set_title("Gaspar class distribution")
    ax.set_xlabel("voto")
    ax.set_ylabel("rows")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def train_pipeline(data_path: str | Path, output_root: str | Path = ".", target_version: str = "v1") -> dict:
    root = Path(output_root)
    metrics_dir = root / "artifacts" / "metrics"
    figures_dir = root / "artifacts" / "figures"
    models_dir = root / "artifacts" / "models"
    reports_dir = root / "reports"
    for directory in [metrics_dir, figures_dir, models_dir, reports_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    raw = load_dataset(data_path)
    prepared = attach_heuristic_target(raw, target_version=target_version, overwrite=True)
    train, test = temporal_split(prepared)

    model = build_model(target_version)
    model.fit(build_feature_frame(train, target_version=target_version), train["voto"])
    predictions = model.predict(build_feature_frame(test, target_version=target_version)) if len(test) else []

    labels = ["GOOD", "FAIR", "POOR"]
    f1_macro = f1_score(test["voto"], predictions, average="macro", zero_division=0) if len(test) else 0.0
    report = classification_report(test["voto"], predictions, labels=labels, zero_division=0, output_dict=True) if len(test) else {}
    matrix = confusion_matrix(test["voto"], predictions, labels=labels) if len(test) else [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    walk_forward = walk_forward_evaluation(prepared, target_version=target_version)

    metrics = {
        "rows": int(len(prepared)),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "f1_macro": float(f1_macro),
        "labels": labels,
        "classification_report": report,
        "confusion_matrix": matrix.tolist() if hasattr(matrix, "tolist") else matrix,
        "feature_columns": feature_columns_for_target(target_version),
        "feature_importance": feature_importance(model),
        "target_source": f"heuristic_{target_version}",
    }

    artifact_stem = "gaspar" if target_version == "v1" else f"gaspar_{target_version}"
    joblib.dump(model, models_dir / f"{artifact_stem}_baseline.joblib")
    (metrics_dir / f"{artifact_stem}_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    walk_forward.to_csv(metrics_dir / f"{artifact_stem}_walk_forward.csv", index=False)

    if len(test):
        display = ConfusionMatrixDisplay(confusion_matrix=matrix, display_labels=labels)
        display.plot(values_format="d")
        plt.title("Gaspar confusion matrix")
        plt.tight_layout()
        plt.savefig(figures_dir / f"{artifact_stem}_confusion_matrix.png")
        plt.close()
    plot_class_distribution(prepared, figures_dir / f"{artifact_stem}_class_distribution.png")
    write_training_report(reports_dir / f"{artifact_stem}_training_report.md", metrics, walk_forward)
    return metrics


def write_training_report(path: Path, metrics: dict, walk_forward: pd.DataFrame) -> None:
    walk_summary = "No disponible por tamano insuficiente del dataset."
    if not walk_forward.empty:
        header = "| fold | train_rows | test_rows | f1_macro |\n| --- | ---: | ---: | ---: |"
        rows = [
            f"| {int(row.fold)} | {int(row.train_rows)} | {int(row.test_rows)} | {float(row.f1_macro):.4f} |"
            for row in walk_forward.itertuples(index=False)
        ]
        walk_summary = "\n".join([header, *rows])

    body = f"""# Gaspar Training Report

## Resumen

- filas: {metrics["rows"]}
- train: {metrics["train_rows"]}
- test: {metrics["test_rows"]}
- F1 macro: {metrics["f1_macro"]:.4f}
- target: heuristica inicial o target provisto por dataset

## Validacion walk-forward

{walk_summary}

## Lectura

Estos resultados validan solo una linea base inicial. La etiqueta actual es provisional y debera calibrarse con resultados reales registrados por Bot C antes de usar Gaspar en operacion.
"""
    path.write_text(body, encoding="utf-8")
