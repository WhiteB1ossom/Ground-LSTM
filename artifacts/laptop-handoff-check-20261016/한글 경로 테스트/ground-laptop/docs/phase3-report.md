# PHASE 3: 학습 및 성능 평가 구현 결과

이 문서는 초기 8-epoch 실행 기록입니다. 2026-10-05의 학습 제어·입력 맥락·임계값 탐색 보완과 최신 검증은 [학습·평가 설계](training-design.md)에 정리했습니다.

## 구현 범위

기존 causal 전처리·train-only scaler·raw event 분할을 그대로 활용하여 PC 학습과 평가를 구현했습니다. Logistic Regression과 작은 단방향 LSTM을 비교하며, 확인된 물리 임계값이 있을 때 threshold baseline을 추가합니다. label이 없거나 일부만 있으면 학습을 중단합니다. 실측 ground_truth는 임의 생성하지 않습니다.

최적 epoch는 validation loss로 선택합니다. validation에서 classification threshold를 선택한 다음 고정해 test를 평가합니다. precision, recall, F1, risk PR-AUC, average precision, 미탐지 FN, 오경보 FP, class별 오류와 혼동행렬을 저장합니다. 이진·다중 클래스 모두 실제 학습과 모델 재로딩을 테스트했습니다.

## 실제 실행 결과 — 소프트웨어 합성 fixture

실측 데이터가 확보되지 않아 별도 labeled software fixture로 파이프라인 동작을 검증했습니다. 이 실험의 label은 합성 state의 명시적 mapping이며 실제 낙뢰 정답이 아닙니다. 따라서 아래 점수는 실제 장치 감지 성능을 의미하지 않습니다.

| 항목 | 결과 |
|---|---|
| prepared dataset | `data/processed/phase3-training-demo` |
| train / validation / test windows | 441 / 147 / 294 |
| sequence length / features | 16 / 20 |
| LSTM | hidden 16, 1 layer, 단방향 |
| 학습 | 8 epochs, balanced class weight, seed 42 |
| best validation epoch | 8 |
| 파라미터 수 | 2,385 |
| Keras 모델 파일 | 53,597 bytes |
| float32 weight 추정 / 입력 tensor | 9,540 / 1,280 bytes |
| PC batch 1 median latency | 약 43.93 ms, Python 호출 포함, 10회 |
| 모델·baseline 재로딩 평가 | 원래 평가와 일치, threshold 재선정 없음 |

현재 실행 결과는 [실험 보고서](../artifacts/models/phase3-verified/report.md), [전체 JSON](../artifacts/models/phase3-verified/report.json), [학습·PR 그래프](../artifacts/models/phase3-verified/loss-and-pr.png), [LSTM 혼동행렬](../artifacts/models/phase3-verified/lstm-confusion.png)에 저장했습니다.

| 모델 | Test precision | Recall | F1 | FN | FP | Risk PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 1.0000 | 1.0000 | 1.0000 | 0 | 0 | 1.0000 |
| LSTM | 0.5000 | 1.0000 | 0.6667 | 0 | 90 | 0.8639 |
| Threshold baseline | 비활성 | — | — | — | — | — |

LSTM의 test 성능은 이 fixture에서 Logistic baseline보다 낮았습니다. validation 결과만 좋다고 일반화를 보장할 수 없으며, 비교 baseline이 필요하다는 점을 실제 출력으로 확인했습니다. 이 결과를 보고 test에 맞춰 threshold나 모델을 재조정하지 않았습니다. threshold baseline은 실제 sensor threshold가 확인되지 않아 비활성입니다.

## 검증

- `.venv-ml`에서 전체 pytest: **118 passed**, 학습 포함 약 53초.
- 기존 데이터 검증·전처리·Ring Buffer 회귀 테스트 통과.
- 실제 이진·3-class LSTM 학습, 최적 checkpoint 저장·재로딩 평가 일치.
- validation 전용 threshold 선택과 recall 목표 미달 경로 검증.
- UNLABELED·부분 label·event 누출·feature 순서 오류·NaN·출처 불일치 차단.
- Logistic JSON 저장·재로딩 출력 일치. 처음 발견한 float32/float64 경로 차이는 계산 dtype을 통일하여 수정.
- scaler·dataset·모델·report SHA-256 확인, 데이터 또는 모델 변경 시 재평가 중단.
- 기존 출력 덮어쓰기 거부, 합성 데이터 이중 opt-in 검증.
- `pip check` 통과, `compileall` 통과, 그래프 직접 확인 완료.

Keras 내부에서 NumPy `__array__`의 copy 인자 관련 DeprecationWarning 15개가 발생했습니다. 경고를 숨기지 않았으며 학습·저장·재평가는 정상 완료했습니다. 실행 환경은 Python 3.12 / TensorFlow 2.21.0 / Keras 3.15.1이며 의존성은 `requirements-ml-lock.txt`에 기록했습니다.

## 보고서·발표에 사용할 수 있는 내용

데이터 품질 검사 → causal 다중 주기 정렬 → event 분리 → train-only scaling → sequence 생성 → baseline/LSTM 학습 → validation threshold → test 지표 → 모델 저장·재평가의 전체 구현과 실제 실행 결과를 설명할 수 있습니다. 기존 Ring Buffer는 제한된 수의 최신 feature를 유지하고 학습 입력과 같은 순서로 sequence를 만드는 구조로 함께 설명할 수 있습니다.

발표에서는 합성 fixture 결과임을 표와 그래프에 명시해야 합니다. 아직 실제 낙뢰 성능, event 감지율, 예측 선행시간 또는 MCU 적합성을 입증한 결과는 없습니다. 실측/실습 데이터와 기업이 확인한 label 의미·센서 기준을 받으면 동일한 학습 CLI로 해당 데이터에 대한 평가를 실행할 수 있습니다.

## 후속 범위

이번 요청 범위인 학습·성능 평가까지 완료했습니다. TFLite 변환/양자화, MCU tensor arena와 실제 latency 측정, Ring Buffer에서 모델 추론으로의 연결, 위험 판단·hysteresis·자동 event recorder는 후속 범위입니다. 현재 PC weight/input 크기 추정만으로 MCU RAM이나 탑재 가능성을 단정하지 않습니다.

자세한 실행 명령과 지표 정의는 [학습 사용법](phase3-usage.md)에 있습니다.
