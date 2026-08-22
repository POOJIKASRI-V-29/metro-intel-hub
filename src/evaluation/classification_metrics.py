"""Classification evaluation metrics for the KMRL platform.

Scope: Accuracy, precision, recall, F1-score, and confusion matrix generation
for evaluating document classification agents. These functions are zero-dependency
and operate on standard Python sequences to ensure high portability in CI/CD environments.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from config.logging import get_logger

logger = get_logger(__name__)


def calculate_accuracy(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    """Computes the overall accuracy of classification predictions.

    Args:
        y_true: A sequence of ground-truth labels.
        y_pred: A sequence of model-predicted labels.

    Returns:
        The ratio of correctly predicted labels to the total number of labels
        (a float between 0.0 and 1.0).

    Raises:
        ValueError: If the sequences have mismatched lengths or are empty.
    """
    _validate_input_lengths(y_true, y_pred)
    
    correct = sum(1 for true, pred in zip(y_true, y_pred) if true == pred)
    return correct / len(y_true)


def calculate_precision_recall_f1(
    y_true: Sequence[str], 
    y_pred: Sequence[str], 
    target_class: str
) -> dict[str, float]:
    """Computes precision, recall, and F1-score for a specific target class.

    Args:
        y_true: A sequence of ground-truth labels.
        y_pred: A sequence of model-predicted labels.
        target_class: The specific class label to evaluate against the rest.

    Returns:
        A dictionary containing the 'precision', 'recall', and 'f1_score' as floats.
        Returns 0.0 for metrics where the denominator is zero (e.g., no predictions made).

    Raises:
        ValueError: If the sequences have mismatched lengths or are empty.
    """
    _validate_input_lengths(y_true, y_pred)

    true_positives = 0
    false_positives = 0
    false_negatives = 0

    for true_label, pred_label in zip(y_true, y_pred):
        if pred_label == target_class and true_label == target_class:
            true_positives += 1
        elif pred_label == target_class and true_label != target_class:
            false_positives += 1
        elif pred_label != target_class and true_label == target_class:
            false_negatives += 1

    precision = 0.0
    if (true_positives + false_positives) > 0:
        precision = true_positives / (true_positives + false_positives)

    recall = 0.0
    if (true_positives + false_negatives) > 0:
        recall = true_positives / (true_positives + false_negatives)

    f1_score = 0.0
    if (precision + recall) > 0:
        f1_score = 2 * (precision * recall) / (precision + recall)

    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score
    }


def generate_confusion_matrix(y_true: Sequence[str], y_pred: Sequence[str]) -> dict[str, dict[str, int]]:
    """Generates a text-based confusion matrix mapping actuals to predictions.

    Args:
        y_true: A sequence of ground-truth labels.
        y_pred: A sequence of model-predicted labels.

    Returns:
        A nested dictionary mapping true classes to a dictionary of predicted class counts.
        Format: `matrix[actual_class][predicted_class] = count`

    Raises:
        ValueError: If the sequences have mismatched lengths or are empty.
    """
    _validate_input_lengths(y_true, y_pred)

    # Initialize a nested dictionary that defaults to 0
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for true_label, pred_label in zip(y_true, y_pred):
        matrix[true_label][pred_label] += 1

    # Convert defaultdicts back to standard dicts for clean serialization
    return {k: dict(v) for k, v in matrix.items()}


def _validate_input_lengths(y_true: Sequence[str], y_pred: Sequence[str]) -> None:
    """Internal helper to ensure label sequences are valid for comparison."""
    if not y_true or not y_pred:
        raise ValueError("Cannot calculate metrics on empty label sequences.")
        
    if len(y_true) != len(y_pred):
        raise ValueError(
            f"Sequence length mismatch: y_true({len(y_true)}) vs y_pred({len(y_pred)})."
        )