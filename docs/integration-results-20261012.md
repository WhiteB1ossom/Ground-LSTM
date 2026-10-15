# 실시간 통합 개발·검증 결과

작성일 2026-10-12 · 실험 `integrated-20261012` · 상태 `PC_COMPLETE_HARDWARE_PENDING`

PC의 입력→전처리→링 버퍼→시퀀스→추론→판단→이벤트 기록→평가를 연결하고 실제 실행했다. 아래 성능은 합성 소프트웨어 시험 결과이며 실제 낙뢰 성능과 MCU 탑재 완료를 의미하지 않는다. 이전 모델·데이터·PPT는 보존했다.

## 요구별 완료와 증거

| 항목 | 현재 상태 | 증거 |
|---|---|---|
| 센서 범위·기준값 | 원문 숫자 보존; 방향·온도 기준 미확정 | `configs/sensor_standard_reference.yaml` |
| 명시 규칙 | gt/ge/lt/le/eq/inside/outside, 차이, 단위, AND/OR, unknown 구현 | `src/models/rules.py`, 경계 테스트 |
| 입력·전처리 | CSV/Parquet 스트림, 같은 시각 센서 병합, 역순·중복 거부, causal 정렬/age/mask | `src/realtime/reader.py`, `stream.py` |
| 연속 입력 | 정답/event_id에 의한 초기화 제거, 획득 세션 경계, 단일 장치 소유 | session 정책 테스트 |
| 학습·선택 | 모델 5개 실제 학습, validation 전용 선택, train-only scaler | `experiment-comparison.json` |
| 추론 계약 | shape·feature·설정·파일 해시 검사, READY 입력만 사용, stateless | `final-audit/audit.json` |
| 알림 판단 | on/off 경계, 연속 확인, NORMAL/RISK/UNAVAILABLE; 장애 중 기존 경보 유지 | `src/realtime/decision.py` |
| 이벤트 기록 | 원본·특징·입력 사유·점수·버전; 전 5초/후 2초, 제한 큐/별도 writer/원자 저장 | calibrated replay events 및 recorder 테스트 |
| 저장 한도 | history 51행, 활성 이벤트 4개, 큐 64개, 최대 파일 1,000개; 초과/실패 명시 | `recorder.py` |
| 재생·평가 | 1x/2x/10x/max 가상 시각 검증, 정상/위험/오류/2시간 정상 | replay summaries, 속도 테스트 |
| 변환 | SavedModel 재로딩, float32/float16/INT8 실행·출력 비교 | export report |
| C++ 준비 | C 배열·정규화 상수, portable 전처리·링·판단; MSVC host 140개 기준 입력 일치 | resource report, host-build.log |
| 실제 장치 | 통신 adapter, TFLM kernel/arena/firmware/MCU deadline 미검증 | 목표 보드·프로토콜 정보 필요 |

확인되지 않은 물리 규칙은 `rules: []`로 비활성이다. 기준 미달/동일/초과는 테스트할 수 있지만 어느 방향이 실제 위험인지 승인한 상태는 아니다. 느린 센서의 장기 추세, 실제 미래 예측, 새 multiclass 의미는 해당 데이터·정답이 없어 활성화하지 않았다. 코드의 비교 연산자는 소프트웨어 기능이며 실제 안전 기준이 아니다.

## 데이터와 모델

- 학습·평가 원본 36,000행 / 60개 획득 시나리오: 36/12/12 세션 분리.
- 오류 원본 6,000행 / 10개: label 없음, 성능 학습에 사용하지 않음.
- 별도 정상 연속 원본 72,000행 / 2시간: 평가 전용, 위험 정답 없음.
- 입력 창: Train 4,860 / Validation 1,620 / Test 1,620 = 8,100.
- 선택 입력: 빠른 센서 5종 × 현재값/결측/age = 15개 특징; shape `1×64×15`, nominal 6.4초, 끝점 간격 6.3초.
- 정렬 100ms, stride 4: 입력 관측을 복제하지 않고 최근 관측을 causal 유지하며 약 400ms마다 창 추론.
- Hidden 16 / 단방향 1층 / 파라미터 2,065 / batch 64 / 최대 50 epochs.
- 실제 32 epochs에서 조기 종료; 최적 검증 손실 가중치는 24회차.
- Label horizon 0: 현재 상태 감지. 점수는 보정된 실제 낙뢰 확률이 아님.

| 후보 | 파라미터 | Validation recall | Validation F1 |
|---|---:|---:|---:|
| lstm16 | 3,025 | 0.9272 | 0.9091 |
| lstm32 | 8,097 | 0.9007 | 0.7371 |
| lstm64 | 24,385 | 0.9073 | 0.9257 |
| lstm16-seed43 | 3,025 | 0.9536 | 0.9028 |
| lstm16-fast-only | 2,065 | 0.9801 | 0.9518 |

선택은 validation만 사용했다. 빠른 센서 후보가 이번 합성 조건에서 선택됐으며 온습도·제한소자 온도가 실제 현장에서 불필요하다는 뜻은 아니다. 8,100개 창은 일부 겹치며 독립적인 8,100개 사건이 아니다. 센서 표의 범위·주기·단위는 참조했지만 정답은 별도 합성 잠재 상태에서 생성했다. 물리 현상을 재현하거나 독립적인 실측 label을 대체하지 않는다.

## 최종 분류와 경보 평가

| Test 모델 | Precision | Recall | F1 | FN | FP |
|---|---:|---:|---:|---:|---:|
| Logistic | 0.9500 | 0.9212 | 0.9354 | 13 | 8 |
| 선택 LSTM | 0.9011 | 0.9939 | 0.9452 | 1 | 18 |

LSTM 혼동행렬: 행=실제 정상/위험, 열=예측 정상/위험, `[[1437,18],[1,164]]`. 정상 분모 1,455개 중 FP18 (1.237%); 위험 분모 165개 중 FN1 (0.606%). LSTM은 Logistic보다 FN이 적고 FP가 많았다. 이전 FP46 실험과 데이터/입력/분할이 달라 개선 비율을 직접 계산하지 않는다.

AI on/off=0.17412868, 연속 2회는 validation에서 정했다. 같은 on/off가 선택되어 이 run에는 추가 히스테리시스 간격이 없으며 기능 자체는 지원한다. 검증 recall 목표는 소프트웨어 후보 필터일 뿐 회사가 승인한 안전 요구가 아니다.

- **입력 FP**: 정답 정상 창에서 점수≥AI 임계값. 테스트 18개.
- **오경보 에피소드**: 유효한 정답 정상 시각에 ENTER가 발생한 횟수. 혼합 시험 0회.
- **정상 경보 시간**: 위험에서 시작한 경보가 정상까지 지속된 시간도 포함. 7.5초 / 유효 정상 579.1초 = 1.295%.
- **사건 감지**: 유효 경보가 위험 구간과 겹치면 감지. 합성 위험 8구간 중 8구간 감지; 지연 중앙값 0.5초 (입력 시각 기준, 미래 예측 선행 시간 아님).
- **Coverage**: 혼합 재생 89.5%. 12개 획득 세션 각각 시작 6.3초는 준비 시간; 위험 구간의 불완전 coverage는 0개.
- **2시간 정상**: 72,000행, 17,985개 추론 창, 새 경보 0회, 정상 경보 시간 0초, coverage 99.9125%. 양성 정답이 없어 recall/F1의 의미 있는 평가가 불가능하며 실제 오경보율 보장이 아님.
- **오류 입력**: 6,000행 원본, 실제 정렬 5,998행, coverage 73.72%. label 없음; FP/FN 계산하지 않음. 구 버전 합성 timestamp의 미세 jitter로 정렬 행 차이가 있었고 이후 생성기는 정수 ns 시간으로 수정; 기존 원본은 유지.

물리 규칙 충족/미충족 × 정답 × 예측의 8칸 평가 집계도 구현했다. 현재 물리 규칙 비활성으로 모든 점수 창의 규칙 조건은 UNKNOWN이다. UNKNOWN을 기준 미달이나 정상으로 바꾸지 않는다. 초과/미달, 동일값, 순간/지속 이탈, 온도 차이와 복합 조건은 확인된 규칙을 입력한 다음 이 표로 해석해야 한다.

## 변환·자원·검증

| 형식 | 파일 bytes | Test 판정 변화 | Test FP/FN | 출력 최대 오차 |
|---|---:|---:|---|---:|
| float32 | 17,360 | 0 | 18/1 | 0.00000009 |
| float16 | 14,260 | 0 | 18/1 | 0.00055665 |
| int8 | 379,576 | 2 | 20/1 | 0.11756663 |

Float 모델은 반복 그래프를 유지했고 INT8은 동일 가중치의 반복 계산을 펼쳤다. INT8은 연산 그래프가 커져 Flash 파일이 더 크고 FP도 2개 늘어 이번 C 배열 후보는 float32다. 실제 MCU 연산자 지원과 자원 예산에 따라 다른 구조가 필요할 수 있다. 중첩 WHILE의 연산자까지 `final-audit/audit.json`에 기록했다. 변환 실패 이력/로그도 보존했다.

Ring 배열 payload 7,866B + 입력 3,840B + 시퀀스 workspace 576B = 알려진 RAM 하한 12,282B. Python 객체·원본 기록·writer·stack·tensor arena·firmware는 포함하지 않았다. Flash/RAM/CPU/board가 미확정이므로 탑재 가능성은 **UNKNOWN**이다. Portable host 빌드는 TFLM adapter 또는 MCU firmware 빌드가 아니다. PC latency를 MCU latency로 사용하지 않는다.

전체 테스트 **165개 통과**. Keras/NumPy 연동의 DeprecationWarning 45건은 별도 보존했다. 파일 hash·입력 계약 변조 거부, 같은 입력 반복과 A/B/A 독립성, READY 실패 입력 재사용 금지, 경계/회복/장애, pre/post/EOF/디스크 실패/큐 초과/파일 한도, 세션·event ID 충돌과 배속을 검사했다. Keras와 float32 LiteRT 연속 재생 7,200행의 상태·판단이 동일하고 점수 최대 오차는 1.1920929e-07였다. C++ 기준 입력 140개 일치도 host에서 실제 실행했다.

## 남은 외부 확인과 보완

1. 센서 기준의 초과/미달·동일값·온도 기준·RMS/peak·입력전압 단위와 사용전압, 실제 허용 경보/미탐지/지연 확정.
2. 실측 원본과 독립 label/onset, 여러 장치·환경의 독립 세션 수집, 실제 조건별 Test 확대 및 재학습.
3. UART/CAN 등의 실제 패킷, 상태·timestamp/clock 동기화 규격과 별도 surge adapter 연결.
4. 목표 MCU/toolchain과 TFLM kernel·arena·firmware·전체 RAM/Flash·최악 처리시간·clock wrap 측정.
5. 필요한 경우 장기 온습도 특징, 확정 multiclass 또는 미래 horizon 모델을 별도 검증. 현재 기능으로 완료를 주장하지 않음.

작동 방법은 [통합 실행 가이드](integration-usage.md), 설계 기준은 [통합 계획](integrated-development-plan-20261012.md) 참조. 결과 기준은 `artifacts/integrated-20261012/run.json`의 stage 경로이며 과거 실패/다른 모델의 export 경로와 혼용하지 않는다.
