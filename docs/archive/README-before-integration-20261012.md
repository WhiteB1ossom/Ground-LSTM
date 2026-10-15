# 낙뢰방호장치 위험감지 데이터 파이프라인

PC에서 센서 데이터를 검증·전처리·학습하고, 이후 MCU에서 작은 LSTM으로 실시간 위험도를 추론하기 위한 모듈형 프로젝트입니다. **현재 PHASE 1·2·3과 Ring Buffer를 구현했습니다.** 실제 기업 데이터, 위험 임계값, MCU 사양은 아직 확보되지 않았습니다.

## 현재 실행 가능한 기능

- 버전 있는 YAML 설정, 활성 센서 10개와 미확정 후보 센서 2개 메타데이터 검증
- 원본 CSV/Parquet 로딩, 파일 SHA-256 기록, source 분리
- timestamp 파싱 실패·시간대 누락·중복·역전 검사
- 센서별 실제 관측 간격과 nominal period 비교
- 결측·NaN·Inf·비수치값·범위 초과·flatline·상태 오류 검사
- reason code를 포함한 JSON 및 Markdown 품질 보고서
- 재현 가능한 다중 주기 합성 데이터 및 선택적 오류 주입
- causal 시간축 정렬, staleness/결측 mask, 선택적 trailing feature
- raw 단계 event/chronological split, purge gap, train-only scaler 및 결측 대체값
- `(batch, sequence_length, features)` 시퀀스, feature 순서·scaler·manifest 저장
- 별도 감지 전후 검증 구간 추출, 실측·실습 출처 및 품질 비교
- 고정 크기 Ring Buffer, 최신 유효 시퀀스 생성, 전처리 연결 CSV demo
- Logistic Regression·단방향 LSTM 학습, early stopping과 최적 모델 저장
- validation 임계값 선택, test precision/recall/F1/PR-AUC/FN/FP·혼동행렬·그래프
- 모델 재로딩 평가, 데이터·모델 해시 검증, 파라미터·PC 지연시간 측정
- pytest 검증

학습·평가 실행은 [학습 사용법](docs/phase3-usage.md), 구현 결과는 [학습·평가 보고서](docs/phase3-report.md)를 참고하세요. TFLite export·실시간 모델 추론·위험 판단·자동 event recorder는 후속 구현 대상입니다. Ring Buffer 실행과 메모리 범위는 [Ring Buffer 사용법](docs/ring-buffer-usage.md)에 있습니다.

발표자료 마지막 센서 표의 범위·단위·관측 주기는 별도 [표준 센서 프로파일](docs/sensor-standard.md)에 반영했습니다. 기존 합성 demo는 임의 단위 실험이며, 이 표준으로 학습한 결과가 아닙니다. 기준값의 판정 의미와 실제 측정 데이터는 확인 후 연결합니다.

2026-10-05에 [학습·평가 설계](docs/training-design.md)를 보완했습니다. 최대 epoch 예산+자동 LR 감소+early stopping, validation score 전체 threshold 탐색, slow sensor age 입력 검사, event group 요약과 validation 전용 모델 추천을 추가했습니다. 실행 명령은 동일합니다.

## 시작하기 (PowerShell)

PHASE 2 전체 CLI·설정·결과 형식은 [전처리 사용법](docs/phase2-usage.md)에 설명했습니다. 데모 생성 후 `.\.venv\Scripts\python -m src.dataset.build --config configs/preprocessing_demo.yaml`로 빌드합니다. 실측/실습 설정은 기업 확인값을 입력하기 전에는 빌드를 중단합니다.

프로젝트 루트에서 실행합니다. 데이터 처리에는 Python 3.11 이상을 사용합니다. **학습 및 전체 테스트에는 Python 3.12의 `.venv-ml` 환경을 사용합니다.** TensorFlow 2.21.0으로 실제 학습을 검증했으며, 기존 Python 3.14 환경은 그대로 보존했습니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m scripts.generate_synthetic_data
.\.venv\Scripts\python -m src.data.inspect --config configs/preprocessing.yaml
py -3.12 -m venv .venv-ml
.\.venv-ml\Scripts\python -m pip install -e ".[dev,ml]"
.\.venv-ml\Scripts\python -m pytest -q
```

이번 실행에 사용한 의존성은 `requirements-lock.txt`에 고정했습니다. 같은 환경을 재현하려면 새 가상환경에서 다음과 같이 설치합니다. 다른 OS/Python에서도 같은 wheel이 제공되는지는 별도 확인해야 합니다.

```powershell
.\.venv\Scripts\python -m pip install -r requirements-lock.txt
.\.venv\Scripts\python -m pip install --no-deps -e .
```

생성기는 기존 원본/metadata를 덮어쓰지 않습니다. 재실행하려면 새 `--output` 경로를 사용합니다.

```powershell
.\.venv\Scripts\python -m scripts.generate_synthetic_data --output data/raw/demo.synthetic.parquet
.\.venv\Scripts\python -m src.data.inspect --input data/raw/demo.synthetic.parquet

# 오류 fixture는 자동 raw 검사와 섞이지 않게 interim에 둡니다.
.\.venv\Scripts\python -m scripts.generate_synthetic_data --inject-faults --output data/interim/faults.synthetic.csv
.\.venv\Scripts\python -m src.data.inspect --input data/interim/faults.synthetic.csv
```

`scripts/generate_synthetic_data.py`를 직접 실행하는 방식도 프로젝트를 editable 설치한 후 사용할 수 있습니다.

검사 CLI 종료 코드는 `0` = 검사 완료 및 invalid 없음, `1` = 검사 완료 및 invalid 발견, `2` = 설정·파일·스키마 오류입니다. `1`일 때에도 보고서를 저장합니다. 범위 초과/flatline/간격 경고만 있으면 `0`입니다. 이 값은 학습 승인·데이터의 물리적 유효성 인증을 의미하지 않습니다.

## 프로젝트 구조와 책임

```text
configs/                  센서·전처리·모델·실시간·MCU·합성 설정
data/raw/                 입력 원본 CSV/Parquet (수정하지 않음)
data/interim/             중간 결과와 오류 fixture
data/processed/           이후 분할 데이터·윈도
data/events/              이후 이벤트 기록
artifacts/scaler/         이후 train-only scaler
artifacts/models/         PC 학습 모델·실험 보고서·그래프
artifacts/tflite/         이후 변환 모델
artifacts/reports/        품질 보고서, Phase 검증 결과
src/data/schema.py        표준 컬럼과 timestamp 해석
src/data/loader.py        원본 로딩·탐색·출처 검사
src/data/quality.py       변경 없는 품질검사
src/data/report.py        JSON/Markdown 원자적 파일 저장
src/data/inspect.py       검사 CLI
src/data/synthetic.py     테스트 시계열 생성
src/utils/config.py       설정 검증·상대 경로 해석
src/preprocessing/        공유 causal 정렬, 설정 검증, train-only scaler
src/features/             feature 순서와 trailing transform
src/dataset/              raw split, label mapping, 윈도, event 구간, 빌드 CLI
src/models/               단방향 LSTM, Logistic/threshold baseline
src/training/             label·provenance 검증, 학습 및 checkpoint
src/evaluation/           validation 임계값, test 지표·그래프, 재평가
src/embedded/             PHASE 4 예정
src/realtime/             RingBuffer, SequenceBuilder, buffer_demo; 추론/판단은 미구현
scripts/                  개발용 CLI
tests/                    동작·회귀 검증
```

설정 내부 경로는 해당 YAML의 디렉터리를 기준으로 해석합니다. CLI의 `--input`, `--output`, `--report-dir`는 현재 작업 디렉터리 기준입니다. 가상환경·원본 데이터·생성 보고서는 `.gitignore`로 제외합니다. 현재 폴더는 Git 저장소가 아니며 기존 파일을 되돌리거나 덮어쓰지 않았습니다.

## 입력 데이터 형식

wide sparse observation 형식입니다. 각 행은 한 acquisition source·device의 관측 timestamp를 나타냅니다. 센서가 그 시각에 새로 측정되지 않았으면 셀을 비워 둡니다. 느린 센서 값을 매 100 ms 행에 반복해서 기록하지 않습니다.

필수 컬럼은 `timestamp`와 `enabled: true`인 센서 컬럼입니다. timestamp 없는 파일은 로더에서 거부하고, 누락된 활성 센서 컬럼은 품질 보고서에 `SENSOR_COLUMN_MISSING`으로 기록합니다. 일부 센서만 제공되면 `configs/sensors.yaml`에서 해당 여부를 명시적으로 조정합니다.

| 센서 | 그룹 | 명목 관측 주기 (초) |
|---|---|---:|
| ground_voltage_a / ground_voltage_b | fast | 약 0.1 |
| leakage_current / input_voltage | fast | 약 1 |
| lightning_sensor | fast | 약 0.1 |
| limiter_temp_a / b / c | slow_context | 약 60 |
| humidity / ambient_temp | slow_context | 미확정 (`null`) |

모든 센서는 `name`, `unit`, `expected_min`, `expected_max`, `nominal_sampling_period`, `threshold`, `missing_value_policy`, `max_staleness`, `enabled`, `group`를 설정합니다. 단위·정상 범위·위험 threshold·stale 제한은 기업 확인 전까지 `null`입니다. `expected_min/max`는 품질 검토 범위이며 위험 판정 `threshold`와 별개입니다.

선택 metadata: `event_id`, `event_timestamp`, `ground_truth`, `device_id`, `sensor_status`, `communication_status`, `source`, `acquisition_kind`. 테스트 전용 metadata: `is_synthetic`, `synthetic_state`. 이 metadata는 feature 이름으로 등록할 수 없으며 PHASE 2에서 센서 feature와 분할·미래값 유입을 검증합니다.

```csv
timestamp,ground_voltage_a,ground_voltage_b,leakage_current,limiter_temp_a,limiter_temp_b,limiter_temp_c,humidity,ambient_temp,input_voltage,lightning_sensor
2026-01-01T00:00:00Z,0.1,0.2,0.01,20,20,20,50,20,220,0
2026-01-01T00:00:00.100Z,0.1,0.2,,,,,,,,0
```

위 값은 형식 설명용이며 단위·물리 기준·임계값을 정의하지 않습니다.

CSV는 UTF-8 또는 UTF-8 BOM을 지원하며 identifier의 선행 0, 빈 셀, 문자열 `NaN/Inf`를 보존합니다. 중복 header·열 개수 불일치·빈 행은 조용히 보정하지 않고 거부합니다. Parquet는 pyarrow null bitmap을 보존하여 비관측과 명시적 NaN을 구분합니다. 로더는 정렬·중복 제거·값 보간·label 생성·원본 쓰기를 수행하지 않습니다.

기업 데이터가 이 스키마를 따르면 `data/raw`에 CSV/Parquet를 넣고 검사 CLI를 실행할 수 있습니다. 다른 단위·epoch timestamp·긴 형태(long format)·이미 채워진 값·센서별 상태 encoding은 원본을 보존한 source adapter가 필요합니다. 셀의 의미는 획득 장치 정의와 확인해야 합니다. 현재 검사기는 전체 파일을 메모리에 읽으며 매우 큰 고속 surge 파일은 별도 chunk/stream adapter가 필요합니다.

### 시간대와 source

기본은 timezone-aware timestamp를 UTC로 변환합니다. naive timestamp는 `TIMESTAMP_TIMEZONE_MISSING`으로 기록합니다. 기업이 naive 시간을 한국 시각으로 명시했다면 다음처럼 설정합니다.

```yaml
timestamp:
  naive_policy: localize
  naive_timezone: Asia/Seoul
  output_timezone: UTC
```

DST의 중복/존재하지 않는 현지 시각과 단위 미지정 숫자 epoch는 추측하지 않고 오류로 남깁니다. timestamp 중복·역전 및 센서 관측 간격은 `device_id`별로 검사합니다. device_id가 없으면 파일을 한 장치의 stream으로 취급합니다.

모니터링과 고속 surge는 별도 source입니다. `input.source`와 파일의 선택 `source`가 충돌하거나 한 파일에 여러 source가 섞이면 거부합니다. surge용 센서 schema/주기는 기업 확인 후 별도 설정 파일과 raw 디렉터리로 관리합니다. PHASE 1에서는 리샘플링하지 않습니다.

## 품질 보고서 해석

보고서 파일명은 `<원본 stem>.<원본 SHA256 앞 12자리>.quality.json/md`입니다. JSON에는 원본 출처·전체 설정 snapshot·센서별 통계·원본 행 번호(0부터)·전체 reason code가 들어갑니다. Markdown은 요약과 최대 100개 issue 예시를 제공합니다. 보고서는 원본 디렉터리 밖에만 저장합니다.

| 분류 | 예 | 의미 |
|---|---|---|
| invalid | 파싱 실패·timestamp 오류·NaN·Inf·비수치·명시적 상태 오류 | 입력/수집 문제; 사용 정책은 후속 단계에서 결정 |
| unavailable | 빈 센서 셀·빈 status | 관측 없음; async 비관측과 패킷 누락을 셀만으로 구별하지 않음 |
| review | 범위 초과·관측 간격 편차·flatline | 조사 필요; 극단적이지만 유효한 물리 신호일 수 있음 |

급격한 변화 자체를 outlier로 삭제하지 않습니다. 범위 초과도 원본 값과 reason을 보존합니다. missing ratio는 전체 파일 행을 분모로 사용하므로 느린 센서에서 높은 비율이 정상적으로 나타납니다. 센서별 실제 관측 시각의 차이를 별도로 계산하여 nominal period와 비교합니다. 미확정 nominal period는 간격 통계만 보고하며 임의 기준을 만들지 않습니다.

`flatline_seconds: null`은 flatline 검사를 비활성화합니다. 사용자가 적절한 기간을 설정하면 반복된 실제 관측만 검사합니다. 명시적 invalid 값 및 nominal cadence를 넘는 공백은 flatline run을 끊습니다. 일정하게 0인 번개 신호 등은 정상일 수 있으므로 항상 review로 기록합니다. 누락된 status 컬럼은 검사 불가이며 정상이라고 인증하지 않습니다. 현재 상태 형식은 행 단위 scalar이며 정상 token을 설정에서 지정합니다. 장치별 복합 상태 정보는 adapter가 필요합니다.

ground_truth가 없거나 빈 값/`UNLABELED`이면 label을 생성하지 않습니다. 보고서는 `UNLABELED`, `PARTIALLY_LABELED`, `LABELED`를 구분하며 label 의미의 유효성은 인증하지 않습니다.

## 합성 데이터의 제한

합성 데이터는 **소프트웨어 파이프라인 검증 전용**입니다. 임의 단위의 파형과 normal / approaching_risk / lightning_event / recovery라는 demonstration state를 만듭니다. 실제 낙뢰 물리·위험 접근 시간·장치 성능을 대표하지 않습니다. 모든 ground_truth는 `UNLABELED`이며 state와 event metadata는 테스트 fixture 식별용입니다.

180초·100 ms grid·60초 demonstration cycle, seed 및 구간 비율은 `configs/synthetic.yaml`에서 변경합니다. 주기가 미확정인 습도/외기온도의 30초 관측은 이 파일의 테스트 설정일 뿐 실제 주기로 사용하지 않습니다. sidecar `.metadata.json`에 purpose·seed를 포함한 설정·SHA-256·오류 주입 여부를 기록합니다. 정상/오류 fixture로 실제 탐지 성능을 평가하면 안 됩니다.

## 이후 구현 계획과 불변 조건

1. **PHASE 2 완료:** causal multi-rate aligner, missing flags/staleness, 선택 feature, event/chronological split을 먼저 수행한 후 train-only scaler 및 윈도 생성. interpolation은 별도 offline analysis에서만 허용. 실제 데이터 운용 설정은 기업 확인 후 입력.
2. **PHASE 3 완료:** threshold baseline·Logistic Regression·작은 단방향 LSTM 비교, early stopping, validation threshold 선정, precision/recall/F1/PR-AUC/FN/FP 및 실험 기록. threshold 미확정이면 해당 baseline 비활성, label 없으면 학습 중지. 합성 label fixture는 별도 명시적 demo에서만 허용. 실제 label mapping 확인 후 실측 학습·평가 필요.
3. **PHASE 4:** hidden 16/32/64 및 feature 축소 실험, SavedModel·TFLite float32/float16/int8, representative dataset, 변환 전후 출력 비교. TFLite Micro operator 지원과 실제 tensor arena를 확인하며 unsupported 변환을 성공으로 보고하지 않음. host latency와 MCU latency를 구분.
4. **PHASE 5:** SensorReader → SensorValidator → MultiRateAligner → RealtimePreprocessor → RingBuffer → SequenceBuilder → InferenceEngine → DecisionEngine → EventRecorder. PC 학습 transform/feature 순서/scaler를 공유. 고정 메모리 ring buffer, advisory 기본, hysteresis, 비차단 pre/post event 기록. 하드웨어는 interface/stub만 제공.
5. **PHASE 6:** CSV replay (1x/2x/10x/max), E2E 검사와 최종 보고서.

**Training = PC. Inference = 목표 MCU. Ring Buffer = 실시간 데이터 관리. Preprocessing = LSTM 입력 생성.** 이 구분은 예정된 최종 architecture이며 현재 MCU 구현은 없습니다. AI advisory는 기존 hard safety logic을 제거하거나 대체하지 않습니다.

MCU 탑재 전 `configs/target_mcu.yaml`의 Flash/RAM/CPU/architecture와 사용 가능한 예산을 확인합니다. 모델·ring/feature buffer·실측 tensor arena·firmware overhead·worst-case latency를 함께 평가해야 합니다. 현재 값은 전부 미확정이며 탑재 가능성을 단정하지 않습니다.

## 검증과 공식 참고 자료

테스트는 원본/순서 보존, CSV/Parquet, source 격리, timezone/DST, 품질 reason code, 다중 주기, flatline, 합성 재현성과 덮어쓰기 거부, 보고서 및 CLI 종료 코드를 검증합니다. PHASE 2에서 train-only scaler, event split 격리, purge gap, causal prefix/stream parity, feature 순서, 미래 target, missing window 제외 및 E2E 빌드 검증을 추가했습니다. Ring Buffer 경계·메모리·batch/stream 일치와 실제 이진/다중 클래스 학습·저장·재평가까지 **125개 테스트가 통과했습니다.** TFLite 테스트는 후속 구현 대상입니다.

입력 파싱과 timezone 처리 정책은 [pandas CSV 공식 문서](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_csv.html), [pandas datetime 공식 문서](https://pandas.pydata.org/docs/reference/api/pandas.to_datetime.html), [pandas I/O 공식 문서](https://pandas.pydata.org/pandas-docs/stable/user_guide/io.html)를 확인했습니다. 테스트 설정은 [pytest 공식 문서](https://pytest.org/en/stable/reference/customize.html)를 따릅니다. 중요한 후속 framework/MCU 지원 결정은 해당 Phase에서 공식 문서를 다시 확인합니다.
