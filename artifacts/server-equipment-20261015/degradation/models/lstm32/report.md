# Training and evaluation report

- Dataset: `8ce234402fe22c4e`
- Software-only synthetic demo: **True**
- Synthetic results cannot establish real lightning detection performance.
- Thresholds are selected on validation only; test is a held-out final evaluation.

| Model | Precision | Recall | F1 | FN | FP | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| logistic | 0.8561 | 0.9953 | 0.9205 | 7 | 250 | 0.9925164165431496 |
| threshold_rule | 1.0000 | 0.9197 | 0.9582 | 120 | 0 | 0.9801233330889481 |
| lstm | 1.0000 | 0.9987 | 0.9993 | 2 | 0 | 0.9999964292634864 |

## Training design

- Stop reason: epoch_budget_reached
- Epochs completed / budget: 50 / 50
- Best validation epoch: 47
- Input nominal window (seconds): 6.4
- Validation-only recommended model: lstm
- Epoch budget completion does not prove convergence or deployment readiness.
- Slow sensors outside the window duration are current context, not learned long-term trends.

## Resources

- LSTM parameters: 9249
- Keras file bytes: 135965
- Host median latency (ms): 125.61099999999999
- Weight/input/recurrent-state estimates exclude tensor arena, backend workspace and firmware.
- No TFLite conversion, MCU latency or deployment feasibility is asserted.

## Threshold baseline

Configured explicit thresholds were evaluated; coverage may be partial.
