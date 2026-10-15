# 통합 실행 가이드

현재 확인한 환경은 Windows, Python 3.12, `.venv-ml`, TensorFlow 2.21.0, LiteRT 2.3.0이다. 명령은 프로젝트 폴더의 PowerShell에서 실행한다. 이번 결과와 의미는 [통합 검증 보고서](integration-results-20261012.md)에 있다.

## 1. 이미 학습한 모델로 작동시키기

재학습 없이 센서 입력→전처리→링 버퍼→추론→판단→이벤트 기록을 실행한다. 아래 입력은 별도 합성 Test 7,200행이다. `run.json`에 연결된 최종 bundle/export와 validation에서 정한 판정 설정을 사용한다.

```powershell
$run = Get-Content .\artifacts\integrated-20261012\run.json -Raw -Encoding UTF8 | ConvertFrom-Json
$bundle = $run.stages.bundle.path
$inputFile = Join-Path $run.stages.calibrated_replay.path 'inputs\heldout.synthetic.csv'
$liteModel = Join-Path $run.stages.export.path 'model-float32.tflite'
$out = Join-Path '.\artifacts' ('replay-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))

.\.venv-ml\Scripts\python.exe -m src.realtime.replay `
  --input $inputFile --bundle $bundle --model tflite --tflite $liteModel `
  --config .\artifacts\integrated-20261012\replay-selected.yaml `
  --speed max --output $out

Get-Content (Join-Path $out 'summary.json') -Raw -Encoding UTF8
```

`--speed 1`은 입력 시간 간격에 맞춰 재생한다. `2`, `10`, `max`도 지원한다. `max`는 대기 없이 처리하되 데이터 timestamp와 경보 시각을 보존한다. CSV의 명시적인 획득 `session_id` 경계에서 준비 상태를 초기화하며 정답이나 `event_id` 변화로 초기화하지 않는다. 첫 64개 시점이 모일 때까지 WARMING_UP이다. 그 후 stride 4에 따라 약 400ms마다 추론한다. 긴 입력 장애가 끝난 뒤에도 유효한 창이 확보돼야 재개한다.

Keras 실행은 같은 명령에서 `--model lstm`으로 바꾸고 `--tflite $liteModel`을 제거한다. Logistic은 `--model logistic`을 사용하되 LSTM에서 선택한 `replay-selected.yaml`을 Logistic에 그대로 적용하지 않는다. Logistic 자체 임계값과 초기 알림 설정은 `--config configs/integration.yaml`에서 사용한다. 비교용 Logistic 알림 정책은 별도 validation calibration으로 선택해야 한다.

생성 결과:

- `timeline.jsonl`, `timeline.000001.jsonl` 등: timestamp, 물리값, 정규화 특징, age, 입력 상태, 점수, 판단과 사유. 파일별 기본 상한은 32 MiB이고 최근 8개까지 보관한다. 실제 남은 파일 순서는 `summary.json`의 `timeline.files`를 사용한다. 모든 행이 새로운 모델 추론은 아니며 READY인 행에 prediction이 있다.
- `summary.json`: window FP/FN, 경보 시작 횟수, 정상 경보 시간, coverage, 지연, 기록 실패, PC 처리시간.
- `events/alarm-*.json`: 원본과 특징, 전 5초/후 2초 기록. 자동으로 생성한 경보 ID이며 실제 낙뢰 정답 ID가 아니다. 미완성 post-event는 사유와 `complete:false`로 보존한다.

이벤트의 `raw_observations`는 정렬 격자 사이에서 수신한 원본까지 보관한다. 타임라인의 `raw_observation`은 각 정렬 시점에서 가장 최근에 수신한 원본 행이며, 그 안의 timestamp가 실제 측정 시각이다. 같은 원본이 여러 정렬 행에 참조될 수 있다. 원본 이력/이벤트별 한도는 `replay.raw_history_capacity`(기본 1,024개), `replay.max_raw_observations_per_event`(기본 4,096개)다. 한도를 넘으면 누락 수와 `raw_observations_truncated`를 표시하고 replay를 `DEGRADED`로 보고한다. 전체 원본은 별도 CSV/Parquet 수집 경로에서 보존한다.

실시간 타이머의 `record_type:STATUS`는 로그에 보관하지만 센서 시간·coverage·분류 지표에는 집계하지 않는다. 후속 평가에도 동일한 `StreamMetrics` / `timeline_metrics`를 사용한다. 이번 오류 처리와 기록 변경은 [추가 버그 수정 기록](realtime-additional-bugfixes-20261013.md)에 정리했다.

float32로 표현할 수 없는 수치가 입력되면 `PREPROCESSING_ERROR / UNAVAILABLE`로 기록하고, 정상 입력으로 새 유효 창을 채운 뒤 복구한다. replay의 `preprocessing_failure_count`와 실시간 서비스의 `processing_failure_count`로 확인한다. 서비스 출력 callback의 `False` 반환은 `output_failure_count`에 집계하며 `None` 반환은 허용한다. 비동기 이벤트 저장의 최종 결과는 `recorder.close()`도 확인한다. 반환 결과 변경이 저장 기록에 영향을 주지 않도록 이벤트 snapshot을 보관한다. [재점검 기록](realtime-review-20261013.md)에 재현과 수정 내용을 정리했다.

기본 모드는 advisory이며 하드웨어 출력은 활성화되지 않는다. 입력이 판정 불가가 되면 기존 경보를 유지하고 정상 해제 증거로 사용하지 않는다. `status:DEGRADED`는 입력 거부·추론 실패·기록 오류 또는 유효 입력 없음이 있었다는 의미다. CLI 종료 코드는 `0=SUCCESS`, `1=DEGRADED`, `2=설정/입력/실행 실패`이다. PowerShell에서 바로 `$LASTEXITCODE`로 확인한다. 원본 디렉터리 아래에는 출력을 쓸 수 없고 기존 출력은 덮어쓰지 않는다.

보관 한도를 넘으면 현재 실행에서 만든 가장 오래된 타임라인 파일을 제거하고 새 파일을 연다. 원본 CSV/Parquet와 이벤트 파일은 이 정책으로 삭제하지 않는다. `timeline.retention_truncated:true`이면 전체 시간의 추적 파일이 남아 있지 않다는 의미다. 전체 평가 집계는 처리한 모든 입력에 대한 값이고, 남은 파일만으로 전체 타임라인을 복원할 수는 없다. 설정의 `replay.timeline_segment_bytes`, `replay.timeline_max_segments`로 한도를 조절한다. 보관된 기록은 `src.realtime.timeline.iter_timeline`으로 읽으며, 기본값에서는 기록이 잘린 분석을 거부한다.

Parquet의 timestamp 열은 timezone이 있는 초·밀리초·마이크로초·나노초형을 지원한다. 기록에서는 ISO 문자열로 저장하고 시간 정렬과 추론에는 기존 timestamp를 사용한다. 설정 YAML에는 최상위 `schema_version: 1`이 필요하다. 현재 `replay-selected.yaml`과 새 설정 생성기도 이 필드를 포함한다.

## 2. 새 환경 준비

기존 `.venv-ml`이 작동하면 다시 설치할 필요가 없다. 새로운 Windows Python 3.12 환경은 다음과 같이 재현한다.

```powershell
py -3.12 -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install -r requirements-integration-lock.txt
.\.venv-ml\Scripts\python.exe -m pip install --no-deps -e .
```

고정 파일은 이번 실행 환경을 기록한 것이다. 다른 OS/Python이나 MCU 도구 체인의 호환성은 별도 확인해야 한다. Microsoft C++ toolchain은 portable host 검증에만 필요하다. 이번 실행에서는 설치된 Visual Studio의 MSVC를 사용했다.

## 3. 전체 데이터 준비·학습·변환·평가 다시 실행

CPU 학습을 포함한다. 결과 경로와 원본 생성 경로는 새 실험 ID를 사용하므로 기존 결과를 덮어쓰지 않는다.

```powershell
$newRun = Join-Path '.\artifacts' ('integrated-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
.\.venv-ml\Scripts\python.exe -m scripts.run_integration `
  --config configs/integration.yaml --output $newRun
```

순서: 60개 학습·평가 시나리오와 10개 오류 fixture, 2시간 정상 데이터 → dataset/scaler → Hidden 16/32/64와 다른 seed → 빠른 센서 특징 축소 → validation 전용 선택 → bundle → SavedModel/LiteRT 변환 → host C++/resource → validation 알림 정책 → Test/오류/정상 재생.

`run.json`의 각 stage에 경로와 성공 여부가 남는다. PC 완료 상태는 `PC_COMPLETE_HARDWARE_PENDING`이다. 변환 형식의 실패/지원 불가 또는 host/재생 검사 미완료는 완료로 통과시키지 않는다. 실제 MCU 미검증은 모든 형식의 `mcu_verified:false`, 자원 `UNKNOWN`으로 남긴다.

학습을 이미 완료했고 export/runtime 문제를 해결한 뒤 재개할 때:

```powershell
.\.venv-ml\Scripts\python.exe -m scripts.resume_integration --run $newRun
```

모델은 재학습하지 않는다. 새 resource/replay 경로를 만들고 호환되는 export가 있으면 재사용한다. 불완전 결과의 단계와 종료 코드를 확인한다. 이전 실패의 로그도 남긴다.

학습 후 실제 bundle/backend 검증:

```powershell
$auditOut = Join-Path $newRun ('audit-' + (Get-Date -Format 'HHmmss-fff'))
.\.venv-ml\Scripts\python.exe -m scripts.verify_integration_run --run $newRun --output $auditOut
.\.venv-ml\Scripts\python.exe -m pytest -q --junitxml "$newRun\tests-final.xml"
```

이 검사는 실제 모델 파일로 eager/compiled 출력, 파일·전처리 설정 변조 거부, A/B/A 독립성, 중첩 그래프의 연산자 목록, 전체 Keras/LiteRT 재생 결과를 비교한다. 긴 실제 대기 없이 배속도 자동 테스트한다.

## 4. 현재 파일 위치

| 자료 | 현재 위치 |
|---|---|
| 학습·평가 합성 원본 | `data/raw/integration/integrated-20261012/training.synthetic.csv` |
| 오류 fixture | 같은 폴더 `faults.synthetic.csv` |
| 2시간 정상 원본 | 같은 폴더 `normal-hour.synthetic.csv` (이름과 달리 실제 2시간) |
| 시나리오 출처·seed·목적 | 같은 폴더 `scenarios.json` |
| 선택 입력 dataset | `artifacts/integrated-20261012/dataset-fast-only/` |
| 원래 10센서 dataset | 같은 run의 `dataset/` |
| 선택 모델과 학습곡선 | 같은 run의 `models/lstm16-fast-only/` |
| 최종 추론 bundle | 같은 run의 `bundle-final/` |
| 확인한 최종 export | 같은 run의 `export-verified-4/` |
| C++ 상수·C 배열·host 로그 | 같은 run의 `resources-verified-3/` |
| Keras 재생·알림 정책 | 같은 run의 `calibrated-3/` |
| 실제 LiteRT 재생·호환성 검사 | 같은 run의 `final-audit/` |
| 실행 증거와 단계 연결 | 같은 run의 `run.json`, `tests-final.xml` |
| 보고서 | `docs/integration-results-20261012.md` |
| 새 PPT·대본 | `output/presentations/그라운드_실시간_통합개발_방경식.pptx`, `그라운드_실시간_통합개발_발표대본_방경식.md` |

새 실행의 숫자 suffix는 달라질 수 있으므로 `run.json`의 stage 경로를 기준으로 한다. 과거의 `export/`, `export-verified-2/` 등 다른 후보 또는 실패 파일과 최종 bundle을 혼용하지 않는다.

## 5. 결과 해석과 실제 데이터 연결

센서 표의 기준값과 AI 점수 임계값은 서로 다른 값이다. 임의로 “센서 기준 초과=위험 정답”으로 라벨을 만들거나 모든 기준에 `>=`를 적용하지 않는다. 실제 물리 규칙은 명시적 `operator`, 단위, 비교 기준이 필요하다. 기준 확인 전 현재 `rules:[]`는 유지한다. 코드의 8칸 분석은 규칙 충족/미충족×정답×예측이며 미확정 규칙은 UNKNOWN으로 따로 센다.

실측 CSV는 timestamp와 활성 센서 열을 포함한 sparse 형식으로 준비한다. 새로 관측하지 않은 셀은 비워 두고 느린 값을 매 행 새 측정값처럼 복제하지 않는다. 실제 UART/CAN wire decode, timestamp 단위/clock 동기화, 장치별 상태 변환, surge source는 확인된 규격의 adapter가 필요하다. PacketAssembler는 이미 해석된 관측을 모으는 경계이며 실제 통신 decoder가 아니다.

실제 배포 전에 independent label/onset, 허용 경보·미탐지·지연, MCU 예산을 확정하고 다시 학습·평가한다. 현재 PC 로그의 가상 데이터 시각과 host의 monotonic clock을 단순 차감해 실제 전송 지연으로 설명하지 않는다. TensorFlow의 oneDNN/CPU 기능 및 native Windows GPU 메시지는 현재 CPU 실행 안내이며 이번 학습 실패를 뜻하지 않는다.
