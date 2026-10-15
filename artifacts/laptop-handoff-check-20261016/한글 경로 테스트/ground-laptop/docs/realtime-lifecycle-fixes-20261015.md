# 2026-10-15 수신·종료·C++ 설정 검증

수신 단절 오판, C++의 잘못된 판정 설정, 이벤트 저장 종료의 무한 대기를 재현하고 수정했다. 학습 모델과 선택한 AI 임계값, 센서 기준값은 유지한다. 기존 실행 결과와 발표자료는 보존하고 수정된 C++ 탑재 준비 파일을 별도 경로로 생성했다.

## 1. 수신 단절과 처리 지연 구분

출력 callback이 멈춰 처리 queue에 입력이 쌓이면, 입력이 계속 도착해도 이전 코드는 `INPUT_TIMEOUT`을 출력했다. 처리한 시각만 보관하고 수신 스레드의 실제 도착 시각을 확인하지 않았기 때문이다.

이제 수신 단계에서 입력 복사본과 host monotonic 도착 시각을 함께 queue에 넣는다. timestamp·출처·장치·순서를 확인한 입력만 수신 감시 기준을 갱신한다. 잘못된 timestamp, 다른 출처·장치, 중복·역순 입력은 단절을 숨기지 못한다. queue가 가득 차도 유효한 입력 도착은 수신 기준을 갱신하고, queue 초과는 별도의 실패 횟수로 기록한다. 센서 값의 품질과 모델 입력의 유효성은 기존 전처리에서 별도로 검사한다.

감시 시각과 최신 도착 기준은 수신 lock 안에서 함께 확인한다. 출력이 막히는 동안 새 입력이 도착하더라도 오래된 기준으로 다음 단절을 판단하지 않는다. 실제 입력 간격이 제한을 넘었다면 처리가 재개된 후에도 `INPUT_TIMEOUT`을 기록한다. 여러 단절이 처리 대기 중 겹치는 경우 가장 최근 기록 하나를 보관하고 합쳐진 기록 수를 `coalesced_input_gap_records`로 보고한다. 전체 단절 이력을 모두 보관하는 구현은 아니다.

처리 대기가 `processing_timeout_seconds` 이상인 입력은 제외하고 `PROCESSING_DELAY / UNAVAILABLE`을 출력한다. 입력 단절 이후에 남은 오래된 queue 데이터도 상태 복구에 사용하지 않는다. 기존 활성 경보를 유지하고 연속 확인 횟수와 입력 창을 초기화해, 새 유효 창이 확보된 뒤 추론을 재개한다. 요약에는 만료된 입력 수 `processing_expired_observations`와 최대 queue 대기시간 `maximum_queue_delay_seconds`를 기록한다.

실시간 서비스는 하나의 worker가 전처리·추론·출력을 담당한다. 이 worker가 멈춘 동안 즉시 상태를 출력하거나 실행 중인 모델·callback을 강제 중단하는 기능은 구현하지 않았다. 위 수정은 worker가 진행할 수 있을 때 수신 단절과 처리 지연을 정확히 구분하고 오래된 입력을 배제한다. 실제 MCU의 독립 watchdog 및 최악 처리시간 검증은 여전히 필요하다.

수신 시각은 모델 특징이나 센서 UTC timestamp에 추가하지 않는다. 파일 replay도 host 시간으로 입력 단절을 판단하지 않는다. monotonic clock의 시간차만 사용하고 센서 시간과 차감하지 않는 원칙은 [Python 공식 time 문서](https://docs.python.org/3.12/library/time.html#time.monotonic)를 따랐다.

## 2. 저장 종료 제한시간과 미완료 보고

저장 스레드가 파일 I/O에서 멈춘 상태에서 queue가 가득 차면, 이전 `close()`는 종료 표식을 넣거나 모든 작업이 끝나기를 무한히 기다렸다.

종료 요청을 `threading.Event`로 전달하고 `join(timeout)`으로 지정한 시간만 기다리도록 수정했다. 종료 표식을 queue에 넣지 않으므로 가득 찬 queue 때문에 종료 요청 자체가 막히지 않는다. worker는 제한시간이 있는 `queue.get()`으로 종료 요청을 확인하며, 동시에 호출한 `close()`도 종료 요청을 중복 처리하지 않는다. 사용한 API는 [Python 공식 Thread.join 문서](https://docs.python.org/3.12/library/threading.html#threading.Thread.join)와 [Queue.get 문서](https://docs.python.org/3.12/library/queue.html#queue.Queue.get)를 확인했다.

`shutdown_timeout_seconds` 기본값은 5초다. 직접 호출하는 경우 `close(timeout_seconds=...)`로 한 번의 대기 제한을 지정한다. 0·음수·bool·NaN·무한대·threading이 지원하지 않는 큰 제한시간은 거부한다.

| 반환 필드 | 의미 |
|---|---|
| `shutdown_complete` | worker가 종료되고 대기 이벤트가 0인지 |
| `shutdown_timed_out` | 이 recorder에서 종료 제한시간을 초과한 이력이 있는지 |
| `pending_events` | 쓰는 중이거나 queue에서 대기 중인 이벤트 수 |
| `writer_failed` | 처리하지 못한 예외로 writer가 종료됐는지 |
| `writer_errors` | 종료 시간 초과·저장 오류·writer 예외의 원인 |

시간을 초과하면 `EVENT_SHUTDOWN_TIMEOUT`과 `DEGRADED`를 보고하고 추가 저장을 비활성화한다. 진행 중인 파일 쓰기를 강제로 취소하지 않으므로 그 파일은 나중에 완료될 수 있다. 다시 `close()`를 호출해 최종 종료와 남은 이벤트를 확인할 수 있으며, 초과 이력은 지우지 않는다. 예상하지 못한 writer 예외도 `EVENT_WRITER_FAILED`로 보고한다. 오류가 worker에서 조용히 사라지거나 미완료 저장이 성공으로 처리되지 않도록 replay는 종료 코드 1을 반환한다.

recorder의 수신·기록 함수는 기존처럼 한 소유 스레드에서 사용하고, 기록을 중단한 뒤 `close()`를 호출한다. 저장 thread를 중단하는 기능이나 디스크 쓰기 시간 보장은 아니다. Python thread의 강제 중단을 지원하지 않는 점과 daemon 종료 특성은 [공식 threading 문서](https://docs.python.org/3.12/library/threading.html)를 참고한다.

## 3. C++ 판정 설정 검증

기존 portable `Decision`은 연속 횟수가 0이면 낮은 점수에서도 경보를 켰다. NaN 임계값에서는 사용할 수 있는 정상 판정으로 반환했고, `off > on` 설정에서는 같은 점수에도 경보가 반복해서 켜지고 꺼졌다.

생성 시 유한한 임계값, `0 <= off <= on <= 1`, 연속 횟수 1 이상을 검사한다. `configuration_valid()`로 확인할 수 있다. 잘못된 설정은 예외를 사용하지 않고 `available:false`, 경보 비활성, 전이 없음으로 반환한다. 정상 설정의 경계값 포함 여부와 장애 중 활성 경보 유지, 연속 확인·해제 동작은 Python 판정과 비교했다.

수정된 코어, 전처리 상수, float32 모델 C 배열, host 시험 파일은 **`artifacts/fixes-20261015/resources/`**에 있다. 과거 `run.json`의 `resources-verified-3/`는 최초 실행 증거로 보존했으므로 이번 설정 검증 수정은 새 경로의 파일을 사용한다. `tflm_adapter.hpp`의 실제 보드 빌드와 kernel·arena 검증은 별도 항목이다.

## 검증 결과

- 새 회귀 시험 30개를 포함한 전체 **285개 테스트** 통과. 입력이 계속 도착하는 동안 출력이 막힌 경우, 단절 STATUS 출력이 막힌 경우, 실제 단절 후 새 입력이 먼저 도착한 경우, queue 초과·오래된 입력 제외·다중 worker 거부를 확인했다.
- 저장 I/O를 의도적으로 막고 queue를 채워도 `close(timeout_seconds=0.1)`가 0.75초 이내에 미완료를 반환했다. 반복·동시 종료, writer 예외, 오류 snapshot 분리, I/O 재개 후 worker 종료와 queue 정리, replay 종료 코드도 확인했다. 시험 허용 오차이며 실제 장치 응답 기한을 뜻하지 않는다.
- MSVC C++17 실제 빌드 및 실행: 전처리·링 기준 입력 **140개**, 잘못된 설정 **12종의 판정 60회**, 유효한 설정 **5종의 Python 판정 비교 90회** 통과. 새 delivery header와 수정된 소스가 일치한다.
- 선택한 실제 float32 LiteRT 모델로 typed Parquet **7,200행** 재생. 기존 Keras 기록과 특징·입력 상태·가용 여부·경보 판단이 일치했다. 최대 점수 차이는 **1.1920928955078125e-7**이며 이벤트 8개의 원본 기록 568개도 일치했다. 실제 Keras 추론 예외에서 판정 불가·경보 유지·이후 복구도 확인했다.
- 모델·bundle·export·선택 설정·발표자료 등의 **98개 파일** SHA256 보존을 확인했다. 재학습과 센서 기준 변경은 하지 않았다. 전체 테스트의 기존 Keras/NumPy DeprecationWarning 45개는 남는다.
- 증거: `artifacts/fixes-20261015/tests-final.xml`, `tests-clock-shutdown.xml`, `portable-verification.json`, `verification/runtime-verification.json`, `verification.json`. 변경 전 코드는 같은 폴더의 `baseline/`에 있다.

검증 범위는 PC 소프트웨어와 portable C++ host 실행이다. 실제 MCU 탑재 성능, 전체 RAM/Flash, 통신 decoder, 실측 낙뢰 성능은 아직 검증하지 않았다.
