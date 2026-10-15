# 낙뢰방호장치 시계열 추론 프로젝트

센서 입력을 전처리하고 학습·평가한 뒤, 링 버퍼 → 모델 추론 → 알림 판단 → 이벤트 기록까지 연결하는 시스템이다. **최신 서버 실험은 대지전위 2 V, 누설전류 2 mA, 제한소자 45℃, 습도 70%의 점검 기준과 10개 센서·누적 서지 횟수를 반영한다. 발표 시연과 노트북 전달 도구를 포함한 전체 테스트 345개가 통과했다.** 실제 장비 고장·낙뢰 성능을 검증한 모델은 아니다.

먼저 [장비 점검·서지 서버 안내](docs/equipment-server-20261015.md)를 따른다. 새 모델은 열화 점검과 서지 활동을 분리하고 39개 특징을 사용한다. 모델 크기나 MCU 메모리로 후보를 제한하지 않는다. 기준 비교와 관측 서지 횟수는 AI 추정과 별도로 출력한다.

**발표에서 실제 구동을 보여주려면 `run-demo.cmd`를 더블클릭한다.** 로컬 화면에서 센서값·링 버퍼·두 모델 점수·경보를 확인할 수 있다. 실행과 시연 순서는 [발표 시연 안내](docs/presentation-demo.md)에 있다. 학습된 모델을 실제로 실행하며 입력은 합성 Test 데이터를 재생한다.

이전 7,200행·15특징 합성 실험은 [통합 실행 가이드](docs/integration-usage.md)에 보존했다. 이전 모델과 발표자료의 1 mA·25℃·60% 설명을 새 서버 실험과 혼용하지 않는다.

다른 Windows PC로 옮길 때는 [노트북 실행 안내](docs/windows-laptop-setup.md)를 따른다. 가상환경을 새로 만들고 데스크탑의 절대경로를 사용하지 않는 LSTM 실행 명령을 제공한다.

노트북용 전달 ZIP을 받은 경우 [START_HERE.md](START_HERE.md)의 문장을 노트북 Codex에 전달하면 된다. [LAPTOP_CODEX_HANDOFF.md](LAPTOP_CODEX_HANDOFF.md)에 설치·실제 모델 검증·시연 실행 순서를 정리했다. `setup-laptop.cmd`는 로컬 가상환경과 고정 버전 설치를 준비한다.

| 자료 | 위치 |
|---|---|
| 최신 기준·서버 모델·실행·검증 | [장비 점검·서지 서버 안내](docs/equipment-server-20261015.md) |
| 이전 통합 실험의 기능·수치·남은 조건 | [통합 검증 결과](docs/integration-results-20261012.md) |
| 실행 명령·환경·결과 파일 | [통합 실행 가이드](docs/integration-usage.md) |
| 전체 요구와 설계 기준 | [통합 개발 계획](docs/integrated-development-plan-20261012.md) |
| Parquet·단절 감시·저장 한도·CLI 수정 | [2026-10-13 버그 수정 기록](docs/realtime-bugfixes-20261013.md) |
| 추론 오류·STATUS 평가·원본 보존·임시 파일 정리 | [추가 버그 수정 기록](docs/realtime-additional-bugfixes-20261013.md) |
| 기록 참조 공유·실시간 출력 실패·수치 오류 복구 | [재점검 기록](docs/realtime-review-20261013.md) |
| 창 유효성·수신 입력 소유권·파일 형식·반복 처리 | [2026-10-14 경계 상황 점검](docs/realtime-boundary-audit-20261014.md) |
| 입력 도착 시각·처리 지연·저장 종료·C++ 설정 검증 | [2026-10-15 수정 및 검증](docs/realtime-lifecycle-fixes-20261015.md) |
| 이전 센서 표 원문과 미확정 의미 | [센서 원문 기록](docs/sensor-standard.md), `configs/sensor_standard_reference.yaml` |
| 새 기준과 해석 근거 | `configs/equipment_server.yaml`의 `criteria_provenance` |
| 최신 서버 모델 연결/단계 | `artifacts/server-equipment-20261015/server-models.json`, 같은 폴더 `run.json` |
| 이전 통합 실험 단계/경로 | `artifacts/integrated-20261012/run.json` |
| 이전 통합 실험 발표자료·대본 | `output/presentations/그라운드_실시간_통합개발_방경식.pptx`, `그라운드_실시간_통합개발_발표대본_방경식.md` |

현재 데이터는 합성 소프트웨어 fixture다. 원래 센서 표는 범위·기준값·주기 사양이며 측정값과 정답을 포함하지 않는다. 새 서버 점검 규칙은 사용자가 제시한 수치와 위임한 기본 해석을 적용하며, 제조사 인증 기준이나 실제 고장 정답으로 확정한 것은 아니다. 모델의 horizon은 0이며 현재 장비 점검 상태와 서지 활동을 분석한다.

현재 구현:

- 서버용 센서 10개·39특징, 누적 서지 증가량/발생률/리셋, 소자별 절대온도·외기온도 차이, 기준전압 편차, 열화 점검·서지 활동 분리, 조건별 오경보 평가.
- 원본 CSV/Parquet 품질 검사, 출처·단위·timestamp 관리, causal 다중 주기 정렬, age/missing 특징, train-only scaler.
- 세션/이벤트 분리, Logistic/LSTM 학습, 검증 데이터 전용 모델·임계값 선택, 별도 Test 평가.
- 단일 장치 연속 입력, 동일 시각 센서 병합, 고정 링·시퀀스, bundle 계약/해시 검사, Keras/Logistic/LiteRT 추론.
- Advisory 정상/위험/판정 불가, 경계·연속 확인·장애 중 경보 유지, 수신 단절과 처리 지연 구분, 제한된 pre/post 기록과 종료 제한시간이 있는 비동기 writer.
- 시간별 replay, 입력/경보/시간/위험 구간/coverage 평가, SavedModel와 float32/float16/INT8 검증.
- 이전 임베디드 실험의 C 배열·전처리 상수·portable C++ 코어, Python과 140개 기준 입력 일치, 잘못된 임계값·횟수 0 거부. 수정 파일은 `artifacts/fixes-20261015/resources/`에 있다. 새 서버의 추가 특징을 해당 코어로 검증한 것은 아니다.

검증 환경은 Windows Python 3.12의 `.venv-ml`, TensorFlow 2.21.0, LiteRT 2.3.0이며 `requirements-integration-lock.txt`에 기록했다. 테스트와 새로운 전체 run은 다음처럼 실행한다.

```powershell
.\.venv-ml\Scripts\python.exe -m pytest -q
$newRun = Join-Path '.\artifacts' ('server-equipment-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
.\.venv-ml\Scripts\python.exe -m scripts.run_equipment_server --config configs/equipment_server.yaml --output $newRun
```

현재 모든 실행은 알림 전용이며 실제 하드웨어 출력은 연결하지 않았다. 목표 보드의 TFLM kernel·arena·전체 RAM/Flash·최악 처리시간, 실제 통신 decoder와 surge adapter는 미검증이다. PC 변환 성공과 host C++ 빌드를 장치 탑재 완료로 해석하지 않는다.

기존 개발 기록은 [이전 README 원본](docs/archive/README-before-integration-20261012.md), [전처리 사용법](docs/phase2-usage.md), [학습 사용법](docs/phase3-usage.md), [이전 학습 결과](docs/phase3-report.md), [이전 링 버퍼 데모](docs/ring-buffer-usage.md)에 보존했다. 날짜와 실험 버전이 다른 숫자를 혼용하지 않는다.
