"""Window-level metrics and validation-only classification threshold selection."""

import numpy as np
from sklearn.metrics import (accuracy_score, auc, average_precision_score, confusion_matrix,
                            f1_score, precision_recall_curve, precision_score, recall_score)


def classification_metrics(y: np.ndarray, probabilities: np.ndarray, *, threshold: float | None, class_count: int) -> dict:
    y = np.asarray(y)
    p = np.asarray(probabilities)
    if y.ndim != 1 or y.dtype.kind not in "iu" or ((y < 0) | (y >= class_count)).any():
        raise ValueError("Invalid classification targets")
    if class_count == 2:
        scores = p.astype(np.float64).reshape(-1)
        if threshold is None or not 0 <= threshold <= 1: raise ValueError("Binary threshold is required")
        predicted = (scores >= threshold).astype(int)
    else:
        if p.shape != (len(y), class_count): raise ValueError("Multiclass probability shape mismatch")
        if not np.allclose(p.sum(axis=1), 1, atol=1e-5): raise ValueError("Multiclass probabilities must sum to one")
        predicted, scores = p.argmax(axis=1), p[:, 1:].sum(axis=1)
    if len(y) != len(predicted) or not len(y) or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Invalid classification probabilities")
    average = "binary" if class_count == 2 else "macro"
    metric_labels = {} if class_count == 2 else {"labels": list(range(class_count))}
    cm = confusion_matrix(y, predicted, labels=list(range(class_count)))
    risk_true, risk_pred = y != 0, predicted != 0
    fn, fp = int((risk_true & ~risk_pred).sum()), int((~risk_true & risk_pred).sum())
    normal_support, risk_support = int((~risk_true).sum()), int(risk_true.sum())
    risk_binary = risk_true.astype(int)
    if len(np.unique(risk_binary)) == 2:
        precision_curve, recall_curve, _ = precision_recall_curve(risk_binary, scores)
        pr_auc = float(auc(recall_curve, precision_curve))
        ap = float(average_precision_score(risk_binary, scores))
    else:
        pr_auc = ap = None
    return {"samples": len(y), "accuracy": float(accuracy_score(y, predicted)),
            "precision": float(precision_score(y, predicted, average=average, zero_division=0, **metric_labels)),
            "recall": float(recall_score(y, predicted, average=average, zero_division=0, **metric_labels)),
            "f1": float(f1_score(y, predicted, average=average, zero_division=0, **metric_labels)),
            "risk_pr_auc_trapezoidal": pr_auc, "risk_average_precision": ap,
            "false_negatives": fn, "false_positives": fp, "confusion_matrix": cm.tolist(),
            "risk_false_negative_rate": fn / risk_support if risk_support else None,
            "risk_false_positive_rate": fp / normal_support if normal_support else None,
            "risk_prevalence": float(risk_true.mean()), "predicted_risk_fraction": float(risk_pred.mean()),
            "per_class": [{"class_id": i, "support": int(cm[i].sum()),
                           "false_negatives": int(cm[i].sum() - cm[i, i]),
                           "false_positives": int(cm[:, i].sum() - cm[i, i])} for i in range(class_count)],
            "threshold": threshold, "scope": "window_level_not_event_level", "averaging": average}


def select_threshold(y: np.ndarray, scores: np.ndarray, settings: dict, *, split: str) -> dict:
    if split != "validation": raise ValueError("Threshold selection is allowed only on validation")
    if set(np.unique(y)) != {0, 1}: raise ValueError("Threshold selection needs both normal and risk validation labels")
    y, scores = np.asarray(y), np.asarray(scores, dtype=np.float64).reshape(-1)
    if len(y) != len(scores) or not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any(): raise ValueError("Invalid validation scores")
    search = settings.get("threshold_search", "configured_candidates")
    if search == "validation_scores":
        # Sorted cumulative counts evaluate every distinct decision boundary in
        # O(n log n), avoiding a full confusion-matrix scan for each threshold.
        thresholds = np.unique(np.concatenate((scores, [.5, np.nextafter(float(scores.max()), np.inf)])))
        thresholds = thresholds[(thresholds >= 0) & (thresholds <= 1)]
        order = np.argsort(scores, kind="stable")
        positives = np.concatenate(([0], np.cumsum(y[order] == 1)))
        below = np.searchsorted(scores[order], thresholds, side="left")
        total_positive = int((y == 1).sum())
        table = []
        for threshold, index in zip(thresholds, below):
            tp = total_positive - int(positives[index])
            fp = len(y) - int(index) - tp
            fn = total_positive - tp
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / total_positive
            f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
            table.append({"threshold": float(threshold), "precision": precision, "recall": recall, "f1": f1,
                          "false_negatives": fn, "false_positives": fp})
    elif search == "configured_candidates":
        table = [classification_metrics(y, scores, threshold=float(t), class_count=2) for t in settings["validation_threshold_candidates"]]
    else: raise ValueError("Unknown threshold_search")
    objective = settings["threshold_objective"]
    eligible = [row for row in table if row["recall"] >= settings["minimum_recall"]]
    target_met = bool(eligible)
    if objective == "max_f1":
        chosen = max(table, key=lambda r: (r["f1"], r["recall"], r["precision"], -abs(r["threshold"] - .5), -r["threshold"]))
        reason = "Highest validation F1; ties favor recall, precision and proximity to 0.5"
    elif objective == "recall_then_f1":
        pool = eligible if eligible else table
        chosen = max(pool, key=lambda r: ((r["f1"] if eligible else r["recall"]), (r["recall"] if eligible else r["f1"]), r["precision"], -abs(r["threshold"] - .5), -r["threshold"]))
        reason = "Highest validation F1 among thresholds meeting the recall target" if eligible else "Recall target was not met; highest validation recall, then F1"
    else: raise ValueError("Unknown threshold objective")
    return {"selected_threshold": chosen["threshold"], "selection_split": "validation", "objective": objective,
            "minimum_recall": settings["minimum_recall"], "recall_target_met": target_met,
            "reason": reason, "search": search, "candidate_count": len(table), "candidates": table}


def event_group_metrics(metadata: dict, probabilities: np.ndarray, *, threshold, class_count: int) -> dict:
    """Aggregate labeled event IDs, without claiming verified physical onset times."""
    if "event_id" not in metadata: return {"status": "unavailable", "reason": "No event IDs"}
    probabilities = np.asarray(probabilities, dtype=np.float64)
    covered = np.isfinite(probabilities).all(axis=1) if probabilities.ndim == 2 else np.isfinite(probabilities)
    predicted = probabilities >= threshold if class_count == 2 else probabilities.argmax(axis=1) != 0
    groups = {}
    for i, event in enumerate(metadata["event_id"].tolist()):
        if not event: continue
        key = (str(metadata["device_id"][i]), str(event))
        groups.setdefault(key, []).append(i)
    detected = missed = uncovered = risk_groups = normal_false_alarm = normal_groups = 0
    for indices in groups.values():
        indices = np.array(indices)
        risk = metadata["y"][indices] != 0
        if risk.any():
            risk_groups += 1
            risk_indices = indices[risk]
            if (covered[risk_indices] & predicted[risk_indices]).any(): detected += 1
            elif covered[risk_indices].all(): missed += 1
            else: uncovered += 1
        else:
            normal_groups += 1
            normal_false_alarm += int((covered[indices] & predicted[indices]).any())
    return {"status": "evaluated" if groups else "unavailable", "scope": "labeled_device_event_groups",
            "risk_groups": risk_groups, "detected_in_positive_windows": detected,
            "missed_risk_groups": missed, "incompletely_covered_risk_groups": uncovered,
            "risk_group_detection_fraction": detected / risk_groups if risk_groups else None,
            "normal_groups": normal_groups, "normal_groups_with_false_alarm": normal_false_alarm,
            "note": "Event ID summaries are retrospective; onset, lead time and alarms/hour are not established."}
