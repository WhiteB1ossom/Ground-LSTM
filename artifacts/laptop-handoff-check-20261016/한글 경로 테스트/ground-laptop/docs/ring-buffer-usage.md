# Ring Buffer 구현과 실행

검증일: 2026-10-04 (Asia/Seoul). 현재 실시간 구성에서 RingBuffer와 SequenceBuilder를 구현했습니다. LSTM 추론, 위험 판단, 자동 event recorder, MCU firmware는 미구현입니다.

## 실행

PHASE 2 데모 산출물이 존재하는 프로젝트 루트에서:

```powershell
.\.venv\Scripts\python -m src.realtime.buffer_demo
```

기본값은 `artifacts/reports/phase2-verification.json`이 가리키는 dataset과 `configs/realtime_demo.yaml`을 사용합니다. 이미 결과가 있다면 새 output을 지정합니다.

```powershell
.\.venv\Scripts\python -m src.realtime.buffer_demo --output artifacts/reports/ring-demo-2.json
```

직접 dataset을 지정할 수도 있습니다.

```powershell
.\.venv\Scripts\python -m src.realtime.buffer_demo --dataset data/processed/862a950365431be7 --config configs/realtime_demo.yaml --output artifacts/reports/ring-demo-3.json
```

dataset의 원본 SHA-256, scaler feature 순서, sequence length/stride/period를 검사합니다. 다른 artifact 설정이나 변경된 raw 파일은 거부합니다. 기본 실제 운용 `configs/realtime.yaml` 값은 미확정으로 남아 있으므로 확인 없이 운용값을 만들지 않습니다.

## 동작

```text
저장된 raw CSV 재생 (최대 속도, PC demo)
→ shared CausalAligner
→ shared FeatureTransform
→ 저장된 FrozenScaler.transform (fit 없음)
→ RingBuffer.append
→ SequenceBuilder.build_into
→ READY / WARMING_UP / INVALID_WINDOW / TIMESTAMP_GAP 등
```

PHASE 2와 비교하기 위해 fixture의 명시적 event 구간마다 정렬 context와 ring을 reset합니다. 실제 장치는 ground-truth event ID를 미리 알 수 없으며, 운용 중 임의로 event ID 기반 reset하면 안 됩니다. 실제 stream에서는 장치 변경·획득 재시작 등 명시적 경계에 reset을 적용해야 합니다. 이 CLI는 고정 replay 속도 옵션·모델을 갖춘 전체 CSV replay 시스템이 아닙니다.

## RingBuffer

`src/realtime/ring_buffer.py`는 capacity × features의 float32 배열, UTC nanosecond int64 timestamp 배열, boolean validity 배열을 시작할 때 할당합니다. append할 때 배열 크기를 늘리지 않고 write position을 순환시켜 oldest row를 덮어씁니다.

- capacity/feature_count는 생성 후 고정됩니다.
- 저장하는 feature는 scaler를 통과한 finite float32입니다. mask 정책과 invalid 행은 validity로 구별합니다.
- timestamp는 timezone-aware pandas Timestamp이며 duplicate/역전/late sample은 거부합니다.
- 입력을 검증한 뒤에만 슬롯을 수정하므로 실패한 append는 기존 데이터를 보존합니다.
- snapshot은 chronological 순서의 독립 복사본입니다. 검사·향후 recorder용으로 사용하며 추가 메모리 할당이 발생합니다.
- copy_latest_into는 caller가 준비한 배열에 chronological 순서로 복사하여 대형 출력 배열을 재사용합니다.
- clear는 storage를 재할당하지 않고 다음 명시적 stream/segment를 시작합니다.
- single owner 방식입니다. concurrent ingest/read는 caller가 serialize해야 하며 lock-free MCU interrupt buffer라고 주장하지 않습니다.

pre-event history를 포함한 용량은 다음과 같습니다.

```text
capacity = sequence_length + ceil(pre_event_seconds / sampling_period_seconds)
```

데모: sequence=16, period=0.1초, pre-event=5초이므로 capacity=66입니다. 이는 software demo 설정이며 물리적 예측 시간 기준이 아닙니다. 현재 ring에는 전처리 feature를 저장합니다. 향후 원본 센서 event recorder에는 별도 bounded raw storage와 pre/post 수집 정책이 필요합니다.

## SequenceBuilder

`src/realtime/sequence_builder.py`는 최신 sequence_length개 행을 caller의 `(1, sequence_length, features)` float32 tensor에 복사합니다. validity가 false인 행, 지정한 period와 다른 간격이 있으면 READY가 아닙니다. stride를 적용하고 같은 sample을 중복으로 READY 처리하지 않습니다. 과거 invalid/gap 행이 최신 window에서 밀려나면 정상 입력을 다시 준비합니다.

`build_into`의 output은 재사용 workspace입니다. status.ready가 true인 경우에만 후속 추론에 전달해야 합니다. 실패 상태일 때 output에 rejected candidate나 이전 내용이 남을 수 있습니다. 이 컴포넌트는 scaling·위험 판정·hardware actuation을 수행하지 않습니다.

## 실제 데모 결과

- replayed samples: 3,600 (6개 fixture segment)
- maximum retained samples: 66
- overwritten samples: 3,204
- ready sequences: 882
- input tensor shape: `(1, 16, 20)`
- ring array payload: 5,874 bytes
- SequenceBuilder workspace payload: 144 bytes
- reusable input tensor: 1,280 bytes
- model inference/hardware actuation: 수행하지 않음

JSON 결과는 `artifacts/reports/ring-buffer-demo.json`, 마지막 retained snapshot은 `ring-buffer-demo.snapshot.npz`에 있습니다. snapshot 저장은 데모 종료 시 명시적으로 수행한 검사 파일이며 위험 감지에 따른 자동 event 기록이 아닙니다.

위 byte 값은 [NumPy 배열 요소의 메모리 크기](https://numpy.org/doc/stable/reference/arrays.ndarray.html)를 합산한 것입니다. Python 객체·DataFrame·전처리·snapshot 복사·모델 tensor arena·운영체제 메모리를 포함하지 않으며 MCU RAM 탑재 가능성 추정도 아닙니다.

## 검증

Ring Buffer 테스트는 multiple wraparound와 deque 기준 결과 비교, 고정 storage 크기, oldest 제거, timestamp 순서, invalid append의 원자성, snapshot 독립성, warm-up/stride/invalid/time gap, clear 후 recovery를 검증합니다. E2E 테스트는 직접 fixture를 생성하여 기존 산출물 없이 실행하고, stream ring의 최종 feature를 PHASE 2 offline 결과와 비교합니다.

```powershell
.\.venv\Scripts\python -m pytest tests/test_ring_buffer.py -q
.\.venv\Scripts\python -m pytest -q
```

다음 단계는 실제 label 기반 모델 학습과 InferenceEngine, DecisionEngine, bounded raw history 및 nonblocking EventRecorder를 연결하는 것입니다. 이번 구현만으로 실제 위험감지·실시간 deadline·MCU 배포가 검증된 것은 아닙니다.
