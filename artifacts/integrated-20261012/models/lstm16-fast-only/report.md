# Training and evaluation report

- Dataset: `c6a243366e130da5`
- Software-only synthetic demo: **True**
- Synthetic results cannot establish real lightning detection performance.
- Thresholds are selected on validation only; test is a held-out final evaluation.

| Model | Precision | Recall | F1 | FN | FP | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| logistic | 0.9500 | 0.9212 | 0.9354 | 13 | 8 | 0.9578144327038215 |
| threshold_rule (disabled) | — | — | — | — | — | — |
| lstm | 0.9011 | 0.9939 | 0.9452 | 1 | 18 | 0.9881448585664063 |

## Training design

- Stop reason: early_stopping
- Epochs completed / budget: 32 / 50
- Best validation epoch: 24
- Input nominal window (seconds): 6.4
- Validation-only recommended model: lstm
- Epoch budget completion does not prove convergence or deployment readiness.
- Slow sensors outside the window duration are current context, not learned long-term trends.

## Resources

- LSTM parameters: 2065
- Keras file bytes: 49757
- Host median latency (ms): 307.2104
- Weight/input/recurrent-state estimates exclude tensor arena, backend workspace and firmware.
- No TFLite conversion, MCU latency or deployment feasibility is asserted.

## Threshold baseline

No confirmed sensor thresholds supplied
