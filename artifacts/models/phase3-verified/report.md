# Training and evaluation report

- Dataset: `d5df91f5e6c9d969`
- Software-only synthetic demo: **True**
- Synthetic results cannot establish real lightning detection performance.
- Thresholds are selected on validation only; test is a held-out final evaluation.

| Model | Precision | Recall | F1 | FN | FP | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| logistic | 1.0000 | 1.0000 | 1.0000 | 0 | 0 | 1.0 |
| threshold_rule (disabled) | — | — | — | — | — | — |
| lstm | 0.5000 | 1.0000 | 0.6667 | 0 | 90 | 0.8638997302376411 |

## Resources

- LSTM parameters: 2385
- Keras file bytes: 53597
- Host median latency (ms): 43.926500000000004
- Weight/input/recurrent-state estimates exclude tensor arena, backend workspace and firmware.
- No TFLite conversion, MCU latency or deployment feasibility is asserted.

## Threshold baseline

No confirmed sensor thresholds supplied
