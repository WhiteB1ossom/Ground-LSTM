# PHASE 2 완료 보고서

검증일: 2026-10-03 (Asia/Seoul). 요청한 1~3회차 보고서를 기준으로 PHASE 2 전처리를 완성했습니다. 실제 LSTM 학습·MCU 배포·Ring Buffer는 이후 Phase입니다.

## 구현 파일

- `src/preprocessing/settings.py`: 빌드 설정 검증과 미확정값 거부
- `src/preprocessing/alignment.py`: 공유 CausalAligner 및 batch grid 정렬
- `src/preprocessing/scaling.py`: train-only Standard/MinMax/Robust, median, JSON artifact
- `src/preprocessing/offline.py`: 모델 입력과 분리한 noncausal 분석 전용 interpolation
- `src/features/transform.py`: current/delta/rate/trailing rolling/missing/age/전위차 feature
- `src/dataset/split.py`: raw event/chronological split, purge gap, event 격리 검증
- `src/dataset/labeling.py`: 명시적 ground_truth mapping과 UNLABELED 처리
- `src/dataset/windows.py`: partition/segment 내부 시퀀스와 미래 target 구성
- `src/dataset/events.py`: 감지 전후 검증용 raw 구간 추출
- `src/dataset/build.py`: 전체 빌드 CLI, staging 저장, manifest, 출처·코드 hash
- `src/data/compare.py`: 실제 실측·실습 source별 schema/품질 비교
- `configs/preprocessing_demo.yaml`, `sensors_demo.yaml`, `synthetic_phase2.yaml`: 소프트웨어 데모 설정
- `configs/preprocessing_field.yaml`, `preprocessing_lab.yaml`: 실제 source별 profile
- `tests/test_phase2.py`: PHASE 2 검증
- `README.md`, `docs/phase2-usage.md`, `requirements-lock.txt`: 실행법과 환경

기존 sensors.yaml에 낙뢰 검지 주파수·거리 후보를 disabled로 추가했습니다. production 설정의 단위·threshold·MCU 사양은 임의 확정하지 않았습니다. loader는 Parquet null bitmap을 보존하고 generator는 소수 길이의 마지막 tick을 정확히 생성하도록 보완했습니다.

## 핵심 설계

정렬부터 먼저 수행하여 분할 사이에 과거 context가 넘어가는 것을 피하기 위해 raw split을 가장 먼저 적용했습니다. 각 split/device/event segment마다 causal 상태를 초기화합니다. source·관측 timestamp·age·missing mask를 관리하고, 명시적 센서/통신 오류 뒤에는 이전 정상값을 재사용하지 않습니다.

스케일러와 결측 대체 median은 valid train rows에서만 fit합니다. feature 순서와 계수를 JSON으로 고정하여 후속 realtime에 재사용합니다. metadata와 미래값은 입력 feature에서 제외합니다. 미래 target은 같은 segment 안에서 선택하고 X는 target 이전의 window까지만 사용합니다.

post-event는 별도 검증 자료입니다. 예측 입력에 미래 구간을 붙이지 않으며, 학습 라벨이 없으면 y=-1과 supervised_training_ready=false로 저장합니다. 합성 데이터는 label이 있어도 실제 supervised training 준비 상태로 표시하지 않습니다.

## 실행 방법

현재 생성한 데모를 다시 빌드하려면 새 결과 디렉터리를 지정합니다.

```powershell
.\.venv\Scripts\python -m src.dataset.build --config configs/preprocessing_demo.yaml --output data/processed/another-demo-run
.\.venv\Scripts\python -m pytest -q
```

데이터 생성부터 실제 기업 설정까지 전체 절차와 NPZ/manifest 형식은 [전처리 사용법](phase2-usage.md)에 있습니다. 기본 production profile은 필요한 설정이 미확정이면 실패합니다.

## 검증 결과

- **pytest: 81 passed, 0 failed** (최종 기능 검증 실행 49.21초).
- compileall: src/scripts/tests 통과.
- pip check: No broken requirements found.
- editable 설치 및 실제 생성/빌드 CLI 실행 성공.
- 데모 raw: 3,600행, 6개 명시적 synthetic event group.
- train: 441개 시퀀스, shape `(441, 16, 20)`.
- validation: 147개 시퀀스, shape `(147, 16, 20)`.
- test: 294개 시퀀스, shape `(294, 16, 20)`.
- float32 X의 finite 값, feature 순서, event 격리, scaler 계수 저장·복원, 원본 SHA-256 보존 확인.
- 모든 target은 UNLABELED(y=-1), 실제 학습 준비=false. 탐지 성능 수치를 만들지 않았습니다.
- validation outlier를 변경해도 train scaler가 바뀌지 않으며 label metadata를 변경해도 X가 바뀌지 않음을 검증.
- offline/realtime transform parity, future-prefix 독립성, staleness 경계, 오류 무효화, drop-window, purge gap, event crossing 오류, Parquet null/NaN 구별, 출처 위장 거부 검증.

실제 산출물 경로·버전·입력 SHA-256은 `artifacts/reports/phase2-verification.json`에 기록했습니다. 이전 데모 결과도 덮어쓰지 않고 보존했습니다.

## 남은 TODO와 적용 한계

기업의 실제 파일·센서 단위/기준점·주기·max_staleness·상태 encoding·label/event 계약·전후 길이 및 예측 horizon 확인이 필요합니다. 원본이 다른 형식이면 adapter가 필요합니다. 실제 실측·실습 데이터 비교와 물리적 위험 성능 검증은 해당 데이터 확보 후 수행합니다.

다음 PHASE 3은 threshold/Logistic Regression baseline, 작은 단방향 LSTM, 학습·평가입니다. PHASE 4 이후에 TFLite/MCU operator·resource 검증, 고정 Ring Buffer·advisory decision·event recorder·CSV replay를 구현합니다. 실제 MCU 탑재 가능성이나 낙뢰 예측 정확도를 아직 주장하지 않습니다.

현재 builder는 batch 메모리 처리이며 긴 획득 중단·대용량 고속 surge·장치별 복합 상태에는 별도 segment/chunk adapter가 필요합니다.
