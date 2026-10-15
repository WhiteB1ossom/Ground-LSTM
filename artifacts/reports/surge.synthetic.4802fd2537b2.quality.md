# Data Quality Report

- File: `surge.synthetic.csv`
- SHA-256: `4802fd2537b2ae89941b0dc79b27f9d88611a8f60ca9c0a22352dada45a4b333`
- Source: monitoring
- Rows: 153000
- Synthetic: True
- Label status: LABELED
- Invalid data detected: False

## Reason counts

| Reason | Count |
|---|---:|
| MISSING_VALUE | 1039465 |
| OUTSIDE_EXPECTED_RANGE | 105 |
| SAMPLING_INTERVAL_DEVIATION | 168 |

## Sensors

| Sensor | Observations | Missing/unavailable ratio | Interval median (s) |
|---|---:|---:|---:|
| ground_voltage_a | 153000 | 0.0 | 0.1 |
| ground_voltage_b | 153000 | 0.0 | 0.1 |
| leakage_current | 15300 | 0.9 | 1.0 |
| limiter_temp_a | 255 | 0.9983333333333333 | 60.0 |
| limiter_temp_b | 255 | 0.9983333333333333 | 60.0 |
| limiter_temp_c | 255 | 0.9983333333333333 | 60.0 |
| humidity | 85 | 0.9994444444444445 | 180.0 |
| ambient_temp | 85 | 0.9994444444444445 | 180.0 |
| input_voltage | 15300 | 0.9 | 1.0 |
| lightning_sensor | 153000 | 0.0 | 0.1 |

## Interpretation

- Raw values and order are unchanged. No filtering or interpolation occurred.
- Empty cells may be asynchronous non-observations, not sensor faults. Ratio uses all file rows.
- Range/flatline/cadence warnings require physical and acquisition context review.
- The raw loader preserves the Parquet null bitmap separately from explicit NaN values.
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
