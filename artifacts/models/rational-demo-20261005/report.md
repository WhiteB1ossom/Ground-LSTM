# Training and evaluation report

- Dataset: `d5df91f5e6c9d969`
- Software-only synthetic demo: **True**
- Synthetic results cannot establish real lightning detection performance.
- Thresholds are selected on validation only; test is a held-out final evaluation.

| Model | Precision | Recall | F1 | FN | FP | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| logistic | 1.0000 | 1.0000 | 1.0000 | 0 | 0 | 1.0 |
| threshold_rule (disabled) | — | — | — | — | — | — |
| lstm | 0.6618 | 1.0000 | 0.7965 | 0 | 46 | 0.9993940721979523 |

## Training design

- Stop reason: epoch_budget_reached
- Epochs completed / budget: 50 / 50
- Best validation epoch: 50
- Input nominal window (seconds): 1.6
- Validation-only recommended model: logistic
- Epoch budget completion does not prove convergence or deployment readiness.
- Slow sensors outside the window duration are current context, not learned long-term trends.

## Resources

- LSTM parameters: 2385
- Keras file bytes: 53597
- Host median latency (ms): 38.2626
- Weight/input/recurrent-state estimates exclude tensor arena, backend workspace and firmware.
- No TFLite conversion, MCU latency or deployment feasibility is asserted.

## Threshold baseline

No confirmed sensor thresholds supplied
