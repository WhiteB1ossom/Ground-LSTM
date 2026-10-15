# Training and evaluation report

- Dataset: `cd999bd348ebaacb`
- Software-only synthetic demo: **True**
- Synthetic results cannot establish real lightning detection performance.
- Thresholds are selected on validation only; test is a held-out final evaluation.

| Model | Precision | Recall | F1 | FN | FP | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| logistic | 1.0000 | 1.0000 | 1.0000 | 0 | 0 | 0.9999999999999998 |
| threshold_rule (disabled) | — | — | — | — | — | — |
| lstm | 1.0000 | 1.0000 | 1.0000 | 0 | 0 | 0.9999999999999999 |

## Training design

- Stop reason: early_stopping
- Epochs completed / budget: 49 / 50
- Best validation epoch: 49
- Input nominal window (seconds): 6.4
- Validation-only recommended model: logistic
- Epoch budget completion does not prove convergence or deployment readiness.
- Slow sensors outside the window duration are current context, not learned long-term trends.

## Resources

- LSTM parameters: 9249
- Keras file bytes: 135965
- Host median latency (ms): 127.77420000000001
- Weight/input/recurrent-state estimates exclude tensor arena, backend workspace and firmware.
- No TFLite conversion, MCU latency or deployment feasibility is asserted.

## Threshold baseline

No confirmed sensor thresholds supplied
