# 낙뢰방호장치 시계열 추론 프로젝트

PC에서 센서 입력을 전처리하고 학습·평가한 뒤, 링 버퍼 → 모델 추론 → 알림 판단 → 이벤트 기록까지 연결하는 시스템이다. **2026-10-12 통합 실행을 완료했고, 2026-10-13 추가 버그 수정까지 반영한 전체 테스트 221개가 통과했다.** 실제 낙뢰 성능과 목표 MCU 탑재 검증은 실측 정답·통신 규격·보드 사양을 확보한 뒤 진행한다.

먼저 [통합 실행 가이드](docs/integration-usage.md)의 **이미 학습한 모델로 작동시키기**를 실행한다. 재학습 없이 7,200개의 합성 Test 입력으로 전체 흐름을 확인할 수 있다. `--speed 1/2/10/max`를 지원한다.

| 자료 | 위치 |
|---|---|
| 현재 기능·수치·남은 조건 | [통합 검증 결과](docs/integration-results-20261012.md) |
| 실행 명령·환경·결과 파일 | [통합 실행 가이드](docs/integration-usage.md) |
| 전체 요구와 설계 기준 | [통합 개발 계획](docs/integrated-development-plan-20261012.md) |
| Parquet·단절 감시·저장 한도·CLI 수정 | [2026-10-13 버그 수정 기록](docs/realtime-bugfixes-20261013.md) |
| 추론 오류·STATUS 평가·원본 보존·임시 파일 정리 | [추가 버그 수정 기록](docs/realtime-additional-bugfixes-20261013.md) |
| 센서 원문 숫자와 미확정 의미 | [센서 기준](docs/sensor-standard.md), `configs/sensor_standard_reference.yaml` |
| 현재 실험 단계/경로 | `artifacts/integrated-20261012/run.json` |
| 새 발표자료·대본 | `output/presentations/그라운드_실시간_통합개발_방경식.pptx`, `그라운드_실시간_통합개발_발표대본_방경식.md` |

현재 데이터는 합성 소프트웨어 fixture다. 센서 표는 범위·기준값·주기 사양이며 측정값과 정답을 포함하지 않는다. 물리 규칙의 초과/미달 방향과 온도 기준은 미확정이므로 자동 위험 판정에 사용하지 않는다. 현재 모델의 horizon은 0이며 입력 종료 시점의 상태 감지다.

현재 구현:

- 원본 CSV/Parquet 품질 검사, 출처·단위·timestamp 관리, causal 다중 주기 정렬, age/missing 특징, train-only scaler.
- 세션/이벤트 분리, Logistic/LSTM 학습, 검증 데이터 전용 모델·임계값 선택, 별도 Test 평가.
- 단일 장치 연속 입력, 동일 시각 센서 병합, 고정 링·시퀀스, bundle 계약/해시 검사, Keras/Logistic/LiteRT 추론.
- Advisory 정상/위험/판정 불가, 경계·연속 확인·장애 중 경보 유지, 제한된 pre/post 기록과 비동기 writer.
- 시간별 replay, 입력/경보/시간/위험 구간/coverage 평가, SavedModel와 float32/float16/INT8 검증.
- C 배열·전처리 상수·portable C++ 코어, Python과 140개 기준 입력 일치, 실제 MCU 자원은 UNKNOWN.

검증 환경은 Windows Python 3.12의 `.venv-ml`, TensorFlow 2.21.0, LiteRT 2.3.0이며 `requirements-integration-lock.txt`에 기록했다. 테스트와 새로운 전체 run은 다음처럼 실행한다.

```powershell
.\.venv-ml\Scripts\python.exe -m pytest -q
$newRun = Join-Path '.\artifacts' ('integrated-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
.\.venv-ml\Scripts\python.exe -m scripts.run_integration --config configs/integration.yaml --output $newRun
```

현재 모든 실행은 알림 전용이며 실제 하드웨어 출력은 연결하지 않았다. 목표 보드의 TFLM kernel·arena·전체 RAM/Flash·최악 처리시간, 실제 통신 decoder와 surge adapter는 미검증이다. PC 변환 성공과 host C++ 빌드를 장치 탑재 완료로 해석하지 않는다.

기존 개발 기록은 [이전 README 원본](docs/archive/README-before-integration-20261012.md), [전처리 사용법](docs/phase2-usage.md), [학습 사용법](docs/phase3-usage.md), [이전 학습 결과](docs/phase3-report.md), [이전 링 버퍼 데모](docs/ring-buffer-usage.md)에 보존했다. 날짜와 실험 버전이 다른 숫자를 혼용하지 않는다.
