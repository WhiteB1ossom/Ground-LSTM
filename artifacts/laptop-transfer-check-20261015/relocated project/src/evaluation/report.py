"""Save auditable metrics and exportable figures without interactive GUI."""

import json
from pathlib import Path

import numpy as np


def write_json(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_summary(path: Path, report: dict):
    lines = ["# Training and evaluation report", "", f"- Dataset: `{report['dataset_version']}`",
             f"- Software-only synthetic demo: **{report['synthetic_demo']}**",
             "- Synthetic results cannot establish real lightning detection performance." if report["synthetic_demo"] else "- Results are window-level metrics on the supplied labeled dataset.",
             "- Thresholds are selected on validation only; test is a held-out final evaluation.", "",
             "| Model | Precision | Recall | F1 | FN | FP | PR-AUC |", "|---|---:|---:|---:|---:|---:|---:|"]
    for name, result in report["models"].items():
        if result["status"] != "evaluated":
            lines.append(f"| {name} ({result['status']}) | — | — | — | — | — | — |")
            continue
        m = result["test"]
        lines.append(f"| {name} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | {m['false_negatives']} | {m['false_positives']} | {m['risk_pr_auc_trapezoidal']} |")
    if "training_control" in report:
        lines += ["", "## Training design", "", f"- Stop reason: {report['training_control']['stop_reason']}",
                  f"- Epochs completed / budget: {report['epochs_completed']} / {report['training_control']['maximum_epochs']}",
                  f"- Best validation epoch: {report['best_epoch']}",
                  f"- Input nominal window (seconds): {report['input_context']['nominal_window_seconds']}",
                  f"- Validation-only recommended model: {report['validation_recommendation']['model']}",
                  "- Epoch budget completion does not prove convergence or deployment readiness.",
                  "- Slow sensors outside the window duration are current context, not learned long-term trends."]
    lines += ["", "## Resources", "", f"- LSTM parameters: {report['resources']['parameters']}",
              f"- Keras file bytes: {report['resources']['keras_file_bytes']}",
              f"- Host median latency (ms): {report['resources']['host_latency_ms']['median']}",
              "- Weight/input/recurrent-state estimates exclude tensor arena, backend workspace and firmware.",
              "- No TFLite conversion, MCU latency or deployment feasibility is asserted.", "",
              "## Threshold baseline", "", report["models"]["threshold_rule"].get("reason", "Configured explicit thresholds were evaluated; coverage may be partial."), ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def plot_results(directory: Path, history: dict, results: dict, test_y: np.ndarray, probabilities: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import precision_recall_curve
    figure, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(history["loss"], label="train")
    axes[0].plot(history["val_loss"], label="validation")
    axes[0].set(xlabel="Epoch index", ylabel="Loss", title="Training loss")
    axes[0].legend()
    for name, p in probabilities.items():
        risk = p.reshape(-1) if p.ndim == 1 else p[:, 1:].sum(axis=1)
        available = np.isfinite(risk)
        if len(np.unique((test_y[available] != 0).astype(int))) != 2: continue
        precision, recall, _ = precision_recall_curve((test_y[available] != 0).astype(int), risk[available])
        axes[1].plot(recall, precision, label=name)
    axes[1].set(xlabel="Recall", ylabel="Precision", title="Test risk PR curve", xlim=(0, 1), ylim=(0, 1.05))
    if axes[1].lines: axes[1].legend()
    figure.suptitle("Window-level evaluation (software fixture only)" if results["synthetic_demo"] else "Window-level evaluation")
    figure.tight_layout()
    figure.savefig(directory / "loss-and-pr.png", dpi=160)
    plt.close(figure)
    for name, result in results["models"].items():
        if result["status"] != "evaluated": continue
        cm = np.asarray(result["test"]["confusion_matrix"])
        figure, axis = plt.subplots(figsize=(4, 4))
        axis.imshow(cm, cmap="Blues")
        for i in range(len(cm)):
            for j in range(len(cm)): axis.text(j, i, str(cm[i, j]), ha="center", va="center")
        axis.set(xlabel="Predicted class", ylabel="True class", title=name, xticks=range(len(cm)), yticks=range(len(cm)))
        figure.tight_layout()
        figure.savefig(directory / f"{name}-confusion.png", dpi=160)
        plt.close(figure)
