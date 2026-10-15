# Data Quality Report

- File: `faults.synthetic.csv`
- SHA-256: `a29d0bc301c059e50847fcd3782ac22a51315e658452638a47f191db548a6be7`
- Source: monitoring
- Rows: 1801
- Synthetic: True
- Label status: UNLABELED
- Invalid data detected: True

## Reason counts

| Reason | Count |
|---|---:|
| COMMUNICATION_ERROR | 1 |
| INF_VALUE | 1 |
| MISSING_VALUE | 12220 |
| NAN_VALUE | 1 |
| NON_NUMERIC_VALUE | 1 |
| SAMPLING_INTERVAL_DEVIATION | 7 |
| SENSOR_STATUS_ABNORMAL | 1 |
| TIMESTAMP_DUPLICATE | 2 |
| TIMESTAMP_PARSE_FAILED | 1 |
| TIMESTAMP_REVERSED | 1 |

## Sensors

| Sensor | Observations | Missing/unavailable ratio | Interval median (s) |
|---|---:|---:|---:|
| ground_voltage_a | 1797 | 0.002220988339811216 | 0.1 |
| ground_voltage_b | 1801 | 0.0 | 0.1 |
| leakage_current | 181 | 0.8995002776235425 | 1.0 |
| limiter_temp_a | 4 | 0.9977790116601888 | 60.0 |
| limiter_temp_b | 4 | 0.9977790116601888 | 60.0 |
| limiter_temp_c | 4 | 0.9977790116601888 | 60.0 |
| humidity | 7 | 0.9961132704053304 | 30.0 |
| ambient_temp | 7 | 0.9961132704053304 | 30.0 |
| input_voltage | 181 | 0.8995002776235425 | 1.0 |
| lightning_sensor | 1801 | 0.0 | 0.1 |

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
| 1 | timestamp | TIMESTAMP_PARSE_FAILED | invalid |
| 3 | timestamp | TIMESTAMP_DUPLICATE | invalid |
| 5 | timestamp | TIMESTAMP_DUPLICATE | invalid |
| 5 | timestamp | TIMESTAMP_REVERSED | invalid |
| 6 | ground_voltage_a | NAN_VALUE | invalid |
| 7 | ground_voltage_a | INF_VALUE | invalid |
| 8 | ground_voltage_a | NON_NUMERIC_VALUE | invalid |
| 11 | ground_voltage_a | MISSING_VALUE | unavailable |
| 4 | ground_voltage_a | SAMPLING_INTERVAL_DEVIATION | review |
| 9 | ground_voltage_a | SAMPLING_INTERVAL_DEVIATION | review |
| 12 | ground_voltage_a | SAMPLING_INTERVAL_DEVIATION | review |
| 4 | ground_voltage_b | SAMPLING_INTERVAL_DEVIATION | review |
| 6 | ground_voltage_b | SAMPLING_INTERVAL_DEVIATION | review |
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
