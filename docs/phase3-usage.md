# 학습 및 성능 평가 사용법

PC에서 전처리된 train/validation/test 시퀀스를 학습하고 평가합니다. 링 버퍼는 이미 별도로 구현되어 있습니다. 현재 모델은 PC의 Keras 모델이며 MCU 배포나 실시간 위험 판단까지 연결한 상태는 아닙니다.

2026-10-05 설정 보완: demo 최대 50 epochs, 일반 최대 100 epochs이며 자동 LR 감소와 early stopping으로 실제 횟수를 결정합니다. validation threshold는 예측 score 경계 전체를 탐색합니다. 새 context 검사와 지표의 의미는 [학습·평가 설계](training-design.md)를 참고하세요. 이전 8-epoch 결과는 과거 검증 기록으로 보존됩니다.

## 환경 설치

프로젝트 루트의 PowerShell에서 실행합니다. 기존 `.venv`를 보존하기 위해 Python 3.12 환경을 따로 만들었습니다. 현재 검증 버전은 Python 3.12, TensorFlow 2.21.0, Keras 3.15.1입니다. 학습에는 TensorFlow가 필요하며 Python 3.14 데이터 처리 환경에서 실행하지 않습니다.

```powershell
py -3.12 -m venv .venv-ml
.\.venv-ml\Scripts\python -m pip install -e ".[dev,ml]"
.\.venv-ml\Scripts\python -m pytest -q
```

이번 환경의 정확한 패키지 목록은 `requirements-ml-lock.txt`입니다. 재현할 때는 새 환경에서 해당 파일을 설치하고 `pip install --no-deps -e .`로 프로젝트를 등록합니다. ML extra의 TensorFlow 조건은 Python 3.14 미만입니다.

## 합성 데이터로 전체 흐름 확인

합성 센서 파형의 demonstration state에 소프트웨어 테스트용 label을 붙이는 전용 경로입니다. `configs/training_fixture.yaml`의 mapping은 물리적 낙뢰 정답이나 예측 선행시간을 정의하지 않습니다. 기존 기본 합성 데이터 생성기는 계속 `UNLABELED`를 생성합니다.

```powershell
.\.venv-ml\Scripts\python -m scripts.prepare_training_demo --dataset-output data/processed/phase3-training-demo
.\.venv-ml\Scripts\python -m src.training.train --dataset data/processed/phase3-training-demo --config configs/model_demo.yaml --output artifacts/models/phase3-demo --synthetic-demo
.\.venv-ml\Scripts\python -m src.evaluation.evaluate --experiment artifacts/models/phase3-demo --dataset data/processed/phase3-training-demo --output artifacts/reports/phase3-reloaded.json
```

기존 출력이 있으면 덮어쓰지 않고 중단합니다. 재실행 시 생성기의 `--output`과 `--dataset-output`, 학습의 `--output`, 재평가의 `--output`에 새 경로를 지정하세요. 이번 검증 결과는 `artifacts/models/phase3-verified`에 있습니다.

합성 데이터는 `--synthetic-demo`와 설정의 `allow_synthetic_demo: true`가 모두 있어야 학습됩니다. 보고서에는 합성 실험 여부를 기록합니다. **합성 데이터 점수로 실제 낙뢰 감지 성능을 주장할 수 없습니다.**

## 실제 데이터 학습

기업에서 확인한 단위·주기·staleness와 ground_truth 의미를 전처리 설정에 입력하고, raw 데이터를 분할한 후 dataset builder로 준비합니다. `configs/model.yaml`의 `labeling.ground_truth_mapping`을 전처리 mapping과 동일하게 설정합니다. binary는 정상 0, 위험 1입니다. multiclass는 0부터 연속된 정수이며 class 0은 정상, 나머지는 위험으로 묶어 risk PR 지표를 계산합니다. multiclass 의미를 확인한 뒤 `multiclass_semantics_confirmed: true`를 설정합니다.

```powershell
.\.venv-ml\Scripts\python -m src.training.train --dataset data/processed/company-dataset --config configs/model.yaml --output artifacts/models/company-experiment-001
```

label이 없거나 일부만 존재하면 학습을 중단합니다. 자동 label 추정은 하지 않습니다. train에는 모든 class, binary validation에는 정상·위험이 모두 있어야 합니다. feature 순서·sequence 길이·출처와 event 분리도 검증합니다. scaler는 기존 dataset builder가 train만으로 적합한 값을 사용합니다.

## 모델과 평가 방식

- Logistic Regression: 각 feature의 마지막 값·평균·표준편차·처음 대비 변화량으로 학습합니다. JSON으로 계수와 class를 저장합니다.
- 작은 단방향 LSTM: 기본 hidden 16, 1 layer이며 binary sigmoid 또는 multiclass softmax 출력입니다. Adam, 학습 seed, 선택적 train-only balanced class weight를 사용합니다.
- Threshold baseline: 확인된 sensor threshold 또는 `baseline.threshold_rules`가 있을 때만 실행합니다. `sensor`, `operator: ge/le`, `value`로 원래 단위의 한계를 설정합니다. 관련 센서가 결측이면 판정을 보류하고 coverage를 별도로 보고합니다. 현재 demo는 임계값 미확정으로 비활성입니다.

LSTM checkpoint와 early stopping은 validation loss를 기준으로 합니다. 최적 모델로 validation 확률을 구한 후 후보 threshold를 비교합니다. 기본 정책은 minimum_recall을 만족하는 후보 중 F1 최대이며, 목표를 못 채우면 recall 우선으로 선택하고 실패 사실을 기록합니다. 이 recall 목표는 평가 설정값이며 물리적 안전 기준은 아닙니다.

선택한 threshold를 고정해 test를 평가합니다. test 결과로 epoch나 threshold를 다시 고르지 않습니다. multiclass는 argmax이며 precision/recall/F1은 모든 configured class에 대한 macro 평균입니다. FN/FP는 정상 대 위험 기준이며 class별 오류도 함께 기록합니다.

PR-AUC는 risk precision-recall 곡선의 사다리꼴 면적입니다. average precision도 별도 저장하여 혼동을 피합니다. 한 종류의 risk label만 있으면 둘 다 `null`입니다. 지표는 window 단위이며 event 감지율·오경보/시간·예측 선행시간은 측정하지 않습니다. 겹치는 window가 있어 표본들이 독립이라는 가정도 하지 않습니다.

## 출력 파일

| 파일 | 내용 |
|---|---|
| `best_model.keras` | validation loss 최적 Keras 모델 |
| `logistic.json` | Logistic baseline 계수 |
| `history.csv`, `history.json` | epoch별 loss·validation 지표 |
| `report.json`, `report.md` | 설정·해시·버전·모델 비교·FN/FP·선택 threshold·자원 측정 |
| `loss-and-pr.png` | 학습 곡선과 test risk PR 곡선 |
| `*-confusion.png` | test 혼동행렬 |
| `test-predictions.npz`, `validation-predictions.npz` | 재현용 label·확률 |
| `scaler.json`, `feature_order.json` | 학습 입력 계약 |
| `model-integrity.json` | 모델·전처리·보고서 파일 SHA-256 |

재평가는 모델과 데이터 파일 해시를 확인하고 저장된 threshold를 그대로 적용합니다. 해시는 파일 변경을 확인하는 용도이며 악의적 위조에 대한 전자서명은 아닙니다. Keras 파일은 신뢰할 수 있는 자체 학습 결과만 사용합니다.

파라미터 수, Keras 파일 크기, float32 weight 추정, 입력 tensor 크기, recurrent state 하한 및 PC batch 1 latency를 보고합니다. PC latency에는 Python 호출이 포함됩니다. 이 값은 MCU 실행시간이나 tensor arena/RAM 요구량을 대변하지 않습니다.

## 설계 근거

Python/Windows 설치와 지원 환경은 [TensorFlow 설치 문서](https://www.tensorflow.org/install/pip)를 확인했습니다. 순방향 시퀀스 처리와 best validation weight 복원은 [Keras LSTM](https://keras.io/api/layers/recurrent_layers/lstm/), [EarlyStopping](https://keras.io/api/callbacks/early_stopping/), [ModelCheckpoint](https://keras.io/api/callbacks/model_checkpoint/)를 따릅니다. 지표 정의와 PR 면적 구분은 [scikit-learn 평가 문서](https://scikit-learn.org/stable/modules/model_evaluation.html)를 참고합니다.
