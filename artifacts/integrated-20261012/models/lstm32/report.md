# Training and evaluation report

- Dataset: `d79bff9541ee61c2`
- Software-only synthetic demo: **True**
- Synthetic results cannot establish real lightning detection performance.
- Thresholds are selected on validation only; test is a held-out final evaluation.

| Model | Precision | Recall | F1 | FN | FP | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| logistic | 0.9620 | 0.9212 | 0.9412 | 13 | 6 | 0.9576332311876087 |
| threshold_rule (disabled) | — | — | — | — | — | — |
| lstm | 0.8579 | 0.9879 | 0.9183 | 2 | 27 | 0.9853539656819194 |

## Training design

- Stop reason: early_stopping
- Epochs completed / budget: 26 / 50
- Best validation epoch: 18
- Input nominal window (seconds): 6.4
- Validation-only recommended model: logistic
- Epoch budget completion does not prove convergence or deployment readiness.
- Slow sensors outside the window duration are current context, not learned long-term trends.

## Resources

- LSTM parameters: 8097
- Keras file bytes: 122143
- Host median latency (ms): 116.19290000000001
- Weight/input/recurrent-state estimates exclude tensor arena, backend workspace and firmware.
- No TFLite conversion, MCU latency or deployment feasibility is asserted.

## Threshold baseline

No confirmed sensor thresholds supplied
