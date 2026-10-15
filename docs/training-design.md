# 학습·평가 설계 보완

2026-10-05에 초기 demo 설정을 보완했습니다. 아래 숫자는 재현 가능한 시작 설정과 계산 예산이며 실측 데이터로 확정한 최적값이나 장치 안전 기준은 아닙니다.

## 학습 제어

| 항목 | 일반 학습 | 소프트웨어 demo |
|---|---:|---:|
| 최대 epochs | 100 | 50 |
| Early stopping patience | 10 | 8 |
| 유의한 validation loss 개선량 | 0.0001 | 0.0001 |
| Adam 초기 learning rate | 0.001 | 0.001 |
| LR plateau patience | 3 | 3 |
| LR 감소 배율 / 하한 | 0.5 / 0.00001 | 동일 |
| Batch size | 32 | 32 |
| Hidden units / layers | 16 / 1 | 동일 |

학습률 감소를 early stopping보다 먼저 시도합니다. validation loss가 개선되지 않으면 학습률을 줄여 추가 학습 기회를 주며, 계속 개선이 없으면 중단합니다. 최적 모델은 전체 epoch 중 validation loss의 엄격한 최솟값 checkpoint입니다. Early stopping의 유의한 개선 기준과 checkpoint의 최솟값 기준은 다를 수 있어 최종 평가에는 저장된 checkpoint를 다시 불러옵니다.

epoch 예산에 도달하면 보고서에 `epoch_budget_reached`를 기록합니다. 마지막 epoch가 최적이면 아직 개선 중일 가능성을 표시하며, 수렴했다고 선언하지 않습니다. epoch별 learning rate도 history에 저장합니다. 같은 데이터·seed·환경의 재현은 확인하되 GPU/OS가 바뀌어도 비트 수준으로 같다고 보장하지 않습니다.

## 표준 센서 주기와 입력

표준 전처리의 시작 설정은 100 ms grid, 64-step sequence, 10-step stride입니다. 이는 nominal 6.4초 window, 실제 첫/마지막 sample 간격 6.3초, 1초마다 평가에 해당합니다. purge gap은 6.4초입니다. 64-step은 MCU 크기를 고려한 초기 빠른 신호 맥락 후보이며 실제 낙뢰 패턴의 충분한 길이라고 확정한 값은 아닙니다.

60초 온도와 60분 습도·외기온도는 짧은 fast window에서 현재 상태를 설명하는 context로 사용합니다. missing indicator와 관측값 age를 함께 입력하여 오래된 값을 새 관측처럼 해석하지 않도록 합니다. 일반 학습 설정은 최소 6.4초 맥락과 slow sensor age feature를 요구하며, 이전 1.6초 dataset은 전처리부터 다시 만들어야 합니다.

시간 단위의 온습도 **추세 자체**가 학습 목표라면 별도 느린 시간축 입력 또는 장기 특징이 필요합니다. 단일 100 ms LSTM을 수십만 step으로 늘리는 변경은 현재 요구사항과 MCU 예산을 확인하기 전에는 하지 않습니다. 허용 staleness와 실제 label 의미는 여전히 명시적인 설정이 필요합니다.

실측 데이터를 확보하면 fast 입력 길이 후보(예: 32/64/128 steps)와 hidden 16/32를 train/validation에서 비교합니다. 서로 다른 길이에서도 같은 raw event partition을 유지하고 가장 긴 입력·horizon에 맞는 공통 purge gap을 사용합니다. 이 표는 실험 계획이며 자동 탐색을 완료했다는 뜻이 아닙니다. 최종 test를 보고 후보를 재선택하지 않습니다.

## 임계값과 모델 비교

이진 threshold를 다섯 고정 후보에 제한하지 않고 validation의 모든 서로 다른 예측 score 경계와 0.5에서 탐색합니다. 동일 score의 중복 처리를 포함해 정렬·누적 집계하므로 O(n log n)으로 평가합니다. 관측 확률이 0.3 미만이어도 적절한 경계를 찾을 수 있습니다. 구형 `configured_candidates` 모드도 지원합니다.

기본은 validation recall 목표 0.9를 만족하는 후보 중 F1 우선입니다. 이 값은 수정 가능한 초기 평가 목표이며 안전 보장 기준이 아닙니다. 목표 미달이면 최고 recall을 선택하고 미달을 기록합니다. 최종 threshold는 test와 재평가에서 고정합니다.

비교 모델 중 validation coverage가 100%인 모델만 대상으로 validation 지표에 따라 추천을 기록합니다. 동률이면 단순한 Logistic Regression을 우선합니다. 부분 coverage threshold rule을 전체 coverage 모델과 같은 조건으로 추천하지 않습니다. test 결과는 추천 모델 선택에 사용하지 않습니다. 추천은 배포 승인이나 물리적 제어 명령이 아닙니다.

## 평가 범위

기존 precision/recall/F1, confusion matrix, PR-AUC, average precision, FN/FP에 정상 window 대비 FP 비율, 위험 window 대비 FN 비율, 위험 label 비율, 위험 예측 비율을 추가했습니다. 클래스 비율을 함께 기록하여 전부 정상 또는 전부 위험으로 예측하는 실패를 확인할 수 있습니다.

`device_id + event_id`별로 위험 정답 window에서 한 번이라도 감지했는지 집계하고 missed/incompletely-covered risk groups를 구분합니다. 모두 정상인 event group의 오경보도 기록합니다. event ID가 없으면 해당 요약은 unavailable입니다. 이 요약은 제공된 label/event group에 대한 사후 평가이며 실제 물리 이벤트 시작시각의 정확성을 증명하지 않습니다.

시간당 오경보, 실제 감지 지연과 예측 선행시간은 현재 계산하지 않습니다. 연속 구간·장애/결측 시간·경보 병합 규칙·실제 onset timestamp가 확정되지 않은 상태에서 숫자를 만들지 않습니다. 겹치는 windows를 독립 표본으로 취급한 신뢰구간도 보고하지 않습니다.

## 검증 및 사용

threshold 경계의 tied scores와 기존 범위 밖 선택, 맥락 길이/age 검사, 부분 관측 이벤트, test 성능과 무관한 validation 추천, 학습률 감소·조기 종료·최적 모델 재평가를 자동 테스트합니다. 큰 `min_delta`를 주어 plateau를 의도적으로 만든 실제 Keras 학습에서도 LR 감소와 조기 종료를 확인합니다.

전체 테스트 125개가 통과했습니다. 보완한 demo를 실제 50 epochs 실행했고 validation loss는 마지막까지 감소하여 `epoch_budget_reached`로 기록했습니다. 재로딩 평가 결과도 일치했습니다. `artifacts/models/rational-demo-20261005`에 모델·보고서·그래프를 저장했습니다. Keras의 NumPy copy 인자 DeprecationWarning은 숨기지 않았으며 학습·평가는 정상 완료했습니다.

이 실행은 이전에 사용한 동일한 합성 fixture의 재실행입니다. test를 새로운 독립 검증 자료로 제시하지 않으며 실측 일반화나 물리적 낙뢰 성능을 입증하지 않습니다. 실제 최종 검증은 설계·모델 선택에 사용하지 않은 새 실측 holdout이 필요합니다.

기존 실행 명령은 그대로이며 `configs/model_demo.yaml`을 사용하면 보완한 demo 설정이 적용됩니다. 이전 모델·그래프·원본 데이터는 보존됩니다. 실제 표준 데이터 학습은 `configs/preprocessing_standard.yaml`에서 실제 acquisition 종류·staleness·label을 설정하고 dataset을 다시 만든 뒤 `configs/model.yaml`로 실행합니다.

## 공식 근거

validation loss의 유의한 개선과 종료 기준은 [Keras EarlyStopping](https://keras.io/api/callbacks/early_stopping/) API를 사용합니다. plateau 시 학습률 감소는 [Keras ReduceLROnPlateau](https://keras.io/api/callbacks/reduce_lr_on_plateau/)를 사용합니다. 데이터와 threshold 선택을 분리하는 원칙은 [scikit-learn threshold tuning 문서](https://scikit-learn.org/stable/modules/classification_threshold.html)를 확인했습니다. 구체적인 epoch/입력 길이/recall 숫자는 공식 문서의 최적값이 아니라 현재 프로젝트를 위한 초기 설정입니다.
