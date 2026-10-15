# PHASE 2 전처리 사용법

3회차 보고서의 전처리 계획을 실행 가능한 코드로 구현했습니다. 모델 학습은 PHASE 3 작업입니다.

## 실행

프로젝트 루트 PowerShell:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m scripts.generate_synthetic_data --config configs/preprocessing_demo.yaml --synthetic-config configs/synthetic_phase2.yaml --output data/raw/phase2-demo.synthetic.csv
.\.venv\Scripts\python -m src.dataset.build --config configs/preprocessing_demo.yaml
.\.venv\Scripts\python -m pytest -q
```

기존 원본·완성된 결과는 덮어쓰지 않습니다. 재빌드는 `--output data/processed/another-demo-run`처럼 새 디렉터리를 지정합니다. `--input`을 반복하여 같은 source의 비중복 파일을 합칠 수 있습니다. 같은 데이터의 CSV/Parquet 복사본을 함께 넣으면 중복 timestamp로 거부합니다. CLI 정상 종료는 0, 설정/입력/빌드 오류는 2입니다.

기본 `configs/preprocessing.yaml`은 실제 운용값을 임의 설정하지 않습니다. alignment period·sequence length·stride·pre/post-event duration·purge gap·sensor max_staleness·acquisition_kind가 미확정이면 빌드를 중단합니다. 데모 단위·시간 길이·staleness는 소프트웨어 테스트용이며 실제 장비 기준으로 사용할 수 없습니다. `future_pipeline`은 PHASE 1의 계획 metadata이며 실제 빌드 설정은 `pipeline`입니다.

## 실측·실습 및 센서 후보

실측은 `configs/preprocessing_field.yaml`, 실습은 `configs/preprocessing_lab.yaml`입니다. `extends`로 기본값을 상속하고 raw 폴더·acquisition_kind를 구분합니다. 경로는 선언한 YAML 기준으로 해석하며 순환 상속을 거부합니다. 원본 metadata의 acquisition_kind/source와 설정이 다르면 실패합니다. synthetic flag가 있는 파일은 실측으로 취급하지 못합니다.

기업 확인값을 입력하고 실제 파일을 제공한 후:

```powershell
.\.venv\Scripts\python -m src.dataset.build --config configs/preprocessing_field.yaml
.\.venv\Scripts\python -m src.dataset.build --config configs/preprocessing_lab.yaml
.\.venv\Scripts\python -m src.data.compare --field-config configs/preprocessing_field.yaml --lab-config configs/preprocessing_lab.yaml
```

비교 CLI는 출처·품질·단위·관측 주기를 JSON으로 저장합니다. 미확정 단위나 다른 단위를 같은 물리량이라고 주장하거나 두 source를 같은 sampling rate로 강제 변환하지 않습니다. 실제 데이터가 없으므로 실제 실측/실습 비교 결과는 아직 없습니다.

2회차의 `lightning_frequency`, `lightning_distance`는 sensors.yaml에 disabled 후보로 추가했습니다. 기업 확인 후 unit/period/staleness 등을 설정하고 켭니다. 고속 surge는 별도 센서 설정과 adapter가 필요합니다.

## 처리 순서

```text
raw 로딩·품질검사·출처 검증
→ raw event/chronological split + purge gap
→ split별 장치·연속 event segment 분리
→ causal 정렬 + staleness/missing mask
→ trailing feature
→ valid train rows로 결측 median·scaler fit
→ 모든 split transform (refit 없음)
→ split/segment 내부 시퀀스 + label target
→ manifest·tensor·scaler·feature order·별도 event 검증 구간 저장
```

timestamp 파싱 오류·중복·역전·필수 컬럼 누락은 품질 보고서를 검토한 후 수집 원인 또는 adapter를 수정해야 합니다. 센서 NaN/Inf/비수치 및 상태 오류는 aligner에서 unavailable로 처리합니다. 급격한 변화와 범위 초과는 원본을 보존합니다.

event split은 모든 행에 event_id가 필요합니다. 정상 배경도 명시적 독립 group ID가 있어야 합니다. auto는 ID가 모두 있으면 event, 하나라도 비었으면 chronological입니다. chronological에서도 같은 nonempty event_id가 여러 split에 걸치면 실패합니다. 실제 event/label을 센서값에서 임의 추정하지 않습니다.

event는 시작 시각 순서로 group을 배정하고 최소 3개 group이 필요합니다. chronological은 전체 장치의 unique timestamp로 경계를 정합니다. purge_gap_seconds는 경계 앞·뒤에 각각 적용합니다. 1초면 경계 양쪽 1초 이내 행을 제외합니다. split이 비거나 사용할 window가 없으면 실패합니다.

각 split/device/연속 event segment마다 정렬·rolling 상태를 초기화합니다. 분할 경계를 넘어 forward fill하지 않습니다. 윈도는 device/event/segment/source/split이나 시간 공백을 가로지르지 않습니다. segment 시작 부분은 context가 없어 결측 또는 warm-up이 될 수 있습니다.

## 시간축 정렬과 missing 정책

CausalAligner.update가 관측을 받고 sample이 grid 시각의 값·mask·age·실제 관측 시각을 반환합니다. late observation·역전·미래 관측을 사용한 sample을 거부합니다. offline과 후속 realtime은 이 클래스를 공유합니다.

빈 셀은 비동기 비관측입니다. 마지막 관측을 유지하되 age >= max_staleness이면 결측 처리합니다. 명시적 오류나 행 단위 통신/sensor 오류는 이전 정상값도 무효화합니다. 새 정상 관측이 도착해야 다시 사용합니다. 느린 센서도 age와 missing mask를 함께 전달합니다.

- forward_fill / limited_forward_fill: causal last-known 값. 안전한 빌드를 위해 둘 다 max_staleness 설정이 필요합니다.
- missing_indicator: 결측 feature를 train-only median으로 대체하고 sensor missing flag를 포함합니다.
- drop_window: 해당 센서가 unavailable인 행을 포함하는 시퀀스를 제외합니다. 전역 stale_action도 지원합니다.
- interpolation: 모델 빌드에서 거부합니다. `src.preprocessing.offline.interpolate_for_analysis`만 별도 분석에 사용하며 noncausal/offline-only 속성을 붙입니다.

상태 컬럼은 현재 행 단위 scalar입니다. 컬럼이 없으면 오류 여부를 인증할 수 없으며 센서별 복합 상태에는 adapter가 필요합니다. 전체 파일을 메모리에 읽는 batch 구현입니다. 한 block이 100만 aligned step을 넘으면 중단하므로 대용량 surge·긴 획득 중단에는 명시적 segment/chunk adapter가 필요합니다.

## feature·scaler·label

기본 feature는 current_value와 sensor missing indicator입니다. delta, rate_of_change, trailing rolling mean/std/min/max를 선택할 수 있습니다. rolling_window_steps를 설정해야 하며 미래값은 사용하지 않습니다. age feature도 선택 가능합니다. event_timestamp/ground_truth/synthetic_state는 입력 feature가 아닙니다.

ground_voltage_difference는 A/B 활성화 및 같은 확인된 단위가 필요합니다. 같은 기준점/calibration인지 기업이 확인한 뒤 켜야 합니다. 두 채널의 실제 관측 시각이 같을 때만 차이를 계산합니다.

StandardScaler·MinMaxScaler·RobustScaler를 설정으로 선택합니다. 결측 대체 median과 scaler는 valid train rows에서만 fit합니다. train에서 유효 관측이 전혀 없는 feature는 임의 값으로 채우지 않고 실패합니다. missing flag는 binary를 유지하며 MinMax는 holdout 값을 clip하지 않습니다.

JSON에 계수·대체값·feature 순서를 저장합니다. FrozenScaler.load는 저장된 계수로만 transform하고 순서가 다르면 실패합니다. pickle을 사용하지 않습니다. artifacts/scaler/<dataset_version>.json에도 보관합니다.

labeling.mapping이 null이거나 ground_truth가 없으면 y=-1입니다. 알려진 label만 mapping하고 모르는 label을 normal로 추정하지 않습니다. label_horizon_seconds=0은 window 종료 시점 label, 양수는 이후 target label입니다. 입력 X는 종료 시각까지이며 target도 같은 split/segment 안에 있어야 합니다. horizon은 alignment period의 정수배입니다.

모든 window target이 labeled이고 synthetic이 아닌 경우에만 supervised_training_ready=true입니다. 이 flag는 물리적 성능이나 label 품질 인증이 아니며 다음 학습 단계에서 확인해야 합니다.

## 결과

`data/processed/<dataset_version>/`에 저장하며 실패한 staging 폴더만 검증된 위치에서 정리합니다.

| 파일 | 내용 |
|---|---|
| manifest.json | 원본 SHA-256·출처·설정·센서 metadata·split/event 배정·윈도 수·라벨 상태 |
| feature_order.json | feature 순서·sequence length·sampling period |
| scaler.json | train-only 변환·대체값 계수 |
| train/validation/test.npz | X(float32), y(int64), source/device/event/segment, 시작·종료·target timestamp |
| train/validation/test.aligned.parquet | 정렬 feature(변환 전)·관측 metadata·validity |
| train/validation/test.events.json | 이벤트 시각·요청한 감지 전후 구간 metadata |
| events/<split>/<hashed-id>.parquet | 별도 pre/detection/post 원본 검증 데이터 |

이벤트 추출은 해당 split의 raw 행만 사용하므로 분할 경계에서 잘릴 수 있습니다. event_id를 경로로 사용하지 않고 hash 파일명으로 저장합니다. detection 시점 ground_truth가 없으면 UNLABELED입니다. post-event는 별도 검증용이며 감지 전 예측 입력으로 붙이지 않습니다.

공식 근거: [pandas backward as-of 정렬](https://pandas.pydata.org/docs/reference/api/pandas.merge_asof.html), [scikit-learn preprocessing](https://scikit-learn.org/stable/modules/preprocessing.html), [scikit-learn leakage 주의사항](https://scikit-learn.org/1.9/common_pitfalls.html). 동일 causal 상태와 age를 realtime에서 공유할 수 있도록 streaming aligner를 구현하고 train에서만 변환 계수를 추정했습니다.
