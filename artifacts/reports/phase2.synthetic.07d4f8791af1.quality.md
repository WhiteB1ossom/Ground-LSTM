# Data Quality Report

- File: `phase2.synthetic.csv`
- SHA-256: `07d4f8791af1a8af4cf29e53f39f0f87e855e6fefb3238e1a562d93f09641c91`
- Source: monitoring
- Rows: 3599
- Synthetic: True
- Label status: UNLABELED
- Invalid data detected: False

## Reason counts

| Reason | Count |
|---|---:|
| MISSING_VALUE | 24431 |

## Sensors

| Sensor | Observations | Missing/unavailable ratio | Interval median (s) |
|---|---:|---:|---:|
| ground_voltage_a | 3599 | 0.0 | 0.1 |
| ground_voltage_b | 3599 | 0.0 | 0.1 |
| leakage_current | 360 | 0.8999722145040289 | 1.0 |
| limiter_temp_a | 6 | 0.9983328702417338 | 60.0 |
| limiter_temp_b | 6 | 0.9983328702417338 | 60.0 |
| limiter_temp_c | 6 | 0.9983328702417338 | 60.0 |
| humidity | 12 | 0.9966657404834677 | 30.0 |
| ambient_temp | 12 | 0.9966657404834677 | 30.0 |
| input_voltage | 360 | 0.8999722145040289 | 1.0 |
| lightning_sensor | 3599 | 0.0 | 0.1 |

## Interpretation

- Raw values and order are unchanged. No filtering or interpolation occurred.
- Empty cells may be asynchronous non-observations, not sensor faults. Ratio uses all file rows.
- Range/flatline/cadence warnings require physical and acquisition context review.
- NaN and absent/null Parquet values may be indistinguishable after decoding.
- Quality inspection does not authorize supervised training or certify MCU suitability.

## Issue examples

Row indexes are 0-based original data rows. Complete details are in JSON.

| Row | Field | Reason | Category |
|---:|---|---|---|
| 1 | leakage_current | MISSING_VALUE | unavailable |
| 2 | leakage_current | MISSING_VALUE | unavailable |
| 3 | leakage_current | MISSING_VALUE | unavailable |
| 4 | leakage_current | MISSING_VALUE | unavailable |
| 5 | leakage_current | MISSING_VALUE | unavailable |
| 6 | leakage_current | MISSING_VALUE | unavailable |
| 7 | leakage_current | MISSING_VALUE | unavailable |
| 8 | leakage_current | MISSING_VALUE | unavailable |
| 9 | leakage_current | MISSING_VALUE | unavailable |
| 11 | leakage_current | MISSING_VALUE | unavailable |
| 12 | leakage_current | MISSING_VALUE | unavailable |
| 13 | leakage_current | MISSING_VALUE | unavailable |
| 14 | leakage_current | MISSING_VALUE | unavailable |
| 15 | leakage_current | MISSING_VALUE | unavailable |
| 16 | leakage_current | MISSING_VALUE | unavailable |
| 17 | leakage_current | MISSING_VALUE | unavailable |
| 18 | leakage_current | MISSING_VALUE | unavailable |
| 19 | leakage_current | MISSING_VALUE | unavailable |
| 21 | leakage_current | MISSING_VALUE | unavailable |
| 22 | leakage_current | MISSING_VALUE | unavailable |
| 23 | leakage_current | MISSING_VALUE | unavailable |
| 24 | leakage_current | MISSING_VALUE | unavailable |
| 25 | leakage_current | MISSING_VALUE | unavailable |
| 26 | leakage_current | MISSING_VALUE | unavailable |
| 27 | leakage_current | MISSING_VALUE | unavailable |
| 28 | leakage_current | MISSING_VALUE | unavailable |
| 29 | leakage_current | MISSING_VALUE | unavailable |
| 31 | leakage_current | MISSING_VALUE | unavailable |
| 32 | leakage_current | MISSING_VALUE | unavailable |
| 33 | leakage_current | MISSING_VALUE | unavailable |
| 34 | leakage_current | MISSING_VALUE | unavailable |
| 35 | leakage_current | MISSING_VALUE | unavailable |
| 36 | leakage_current | MISSING_VALUE | unavailable |
| 37 | leakage_current | MISSING_VALUE | unavailable |
| 38 | leakage_current | MISSING_VALUE | unavailable |
| 39 | leakage_current | MISSING_VALUE | unavailable |
| 41 | leakage_current | MISSING_VALUE | unavailable |
| 42 | leakage_current | MISSING_VALUE | unavailable |
| 43 | leakage_current | MISSING_VALUE | unavailable |
| 44 | leakage_current | MISSING_VALUE | unavailable |
| 45 | leakage_current | MISSING_VALUE | unavailable |
| 46 | leakage_current | MISSING_VALUE | unavailable |
| 47 | leakage_current | MISSING_VALUE | unavailable |
| 48 | leakage_current | MISSING_VALUE | unavailable |
| 49 | leakage_current | MISSING_VALUE | unavailable |
| 51 | leakage_current | MISSING_VALUE | unavailable |
| 52 | leakage_current | MISSING_VALUE | unavailable |
| 53 | leakage_current | MISSING_VALUE | unavailable |
| 54 | leakage_current | MISSING_VALUE | unavailable |
| 55 | leakage_current | MISSING_VALUE | unavailable |
| 56 | leakage_current | MISSING_VALUE | unavailable |
| 57 | leakage_current | MISSING_VALUE | unavailable |
| 58 | leakage_current | MISSING_VALUE | unavailable |
| 59 | leakage_current | MISSING_VALUE | unavailable |
| 61 | leakage_current | MISSING_VALUE | unavailable |
| 62 | leakage_current | MISSING_VALUE | unavailable |
| 63 | leakage_current | MISSING_VALUE | unavailable |
| 64 | leakage_current | MISSING_VALUE | unavailable |
| 65 | leakage_current | MISSING_VALUE | unavailable |
| 66 | leakage_current | MISSING_VALUE | unavailable |
| 67 | leakage_current | MISSING_VALUE | unavailable |
| 68 | leakage_current | MISSING_VALUE | unavailable |
| 69 | leakage_current | MISSING_VALUE | unavailable |
| 71 | leakage_current | MISSING_VALUE | unavailable |
| 72 | leakage_current | MISSING_VALUE | unavailable |
| 73 | leakage_current | MISSING_VALUE | unavailable |
| 74 | leakage_current | MISSING_VALUE | unavailable |
| 75 | leakage_current | MISSING_VALUE | unavailable |
| 76 | leakage_current | MISSING_VALUE | unavailable |
| 77 | leakage_current | MISSING_VALUE | unavailable |
| 78 | leakage_current | MISSING_VALUE | unavailable |
| 79 | leakage_current | MISSING_VALUE | unavailable |
| 81 | leakage_current | MISSING_VALUE | unavailable |
| 82 | leakage_current | MISSING_VALUE | unavailable |
| 83 | leakage_current | MISSING_VALUE | unavailable |
| 84 | leakage_current | MISSING_VALUE | unavailable |
| 85 | leakage_current | MISSING_VALUE | unavailable |
| 86 | leakage_current | MISSING_VALUE | unavailable |
| 87 | leakage_current | MISSING_VALUE | unavailable |
| 88 | leakage_current | MISSING_VALUE | unavailable |
| 89 | leakage_current | MISSING_VALUE | unavailable |
| 91 | leakage_current | MISSING_VALUE | unavailable |
| 92 | leakage_current | MISSING_VALUE | unavailable |
| 93 | leakage_current | MISSING_VALUE | unavailable |
| 94 | leakage_current | MISSING_VALUE | unavailable |
| 95 | leakage_current | MISSING_VALUE | unavailable |
| 96 | leakage_current | MISSING_VALUE | unavailable |
| 97 | leakage_current | MISSING_VALUE | unavailable |
| 98 | leakage_current | MISSING_VALUE | unavailable |
| 99 | leakage_current | MISSING_VALUE | unavailable |
| 101 | leakage_current | MISSING_VALUE | unavailable |
| 102 | leakage_current | MISSING_VALUE | unavailable |
| 103 | leakage_current | MISSING_VALUE | unavailable |
| 104 | leakage_current | MISSING_VALUE | unavailable |
| 105 | leakage_current | MISSING_VALUE | unavailable |
| 106 | leakage_current | MISSING_VALUE | unavailable |
| 107 | leakage_current | MISSING_VALUE | unavailable |
| 108 | leakage_current | MISSING_VALUE | unavailable |
| 109 | leakage_current | MISSING_VALUE | unavailable |
| 111 | leakage_current | MISSING_VALUE | unavailable |
