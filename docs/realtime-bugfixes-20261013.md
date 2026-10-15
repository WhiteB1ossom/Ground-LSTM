# 실시간 처리 버그 수정 기록

작성일: 2026-10-13. 학습 모델·센서 기준·AI 임계값은 기존 실험을 사용한다.

| 문제 | 수정 | 검증 |
|---|---|---|
| Parquet datetime을 JSON으로 저장할 때 오류 | Python datetime과 pandas Timestamp를 공통 ISO 문자열로 변환 | 초/ms/us/ns형 Parquet와 CSV의 전처리·판단 일치, 이벤트 저장 |
| 입력이 완전히 끊기면 상태 갱신 없음 | 단일 소유자 수신 루프가 빈 큐에서도 monotonic clock으로 timeout 검사 | 실제 작업 스레드에서 새 입력 없이 판정 불가 발생 |
| 타임라인 파일 크기 제한 없음 | 기본 파일당 32 MiB, 최근 8개 보관, 현재 실행 소유 파일만 교체 | UTF-8 바이트 상한, 순서, 다른 파일 보존, 저장 실패 |
| 실패를 기록하고도 CLI 종료 코드 0 | SUCCESS=0, DEGRADED=1, 설정/입력/실행 실패=2 | 입력 거부, 추론 실패, 이벤트/타임라인 저장 실패, 빈 입력 |
| 선택된 replay YAML에 버전 필드 누락 | 기존 파일과 두 설정 생성기에 schema_version:1 추가 | 실제 설정 검사와 별도 CLI 프로세스 |

## 단절 감시 연결

`RealtimePipeline.poll()`은 호스트 수신 무응답을 확인한다. `RealtimeService.run()`이 이를 주기적으로 호출하므로 입력이 없는 동안에도 상태가 바뀐다. 기본 무응답 상한은 1초, 기본 검사 간격은 최대 100ms이다. 이 값은 PC 소프트웨어 기본 설정이며 장치의 승인된 위험 기준이나 MCU 처리 기한이 아니다.

단절 시 `STATUS / INPUT_TIMEOUT / UNAVAILABLE`를 내보내고 기존 경보를 유지한다. 대기 중인 post-event 기록에는 `complete:false`, `INPUT_TIMEOUT` 사유를 붙인다. 과거 특징과 시퀀스를 초기화하고 수신 재개 후 새 유효 창을 확보한다. 무응답 동안 가짜 센서 관측이나 정답을 만들지 않으며 호스트 monotonic 시간을 센서 timestamp와 섞지 않는다.

수신 adapter 연결 예시:

```python
from threading import Event, Thread
from src.realtime.inference import InferenceEngine
from src.realtime.stream import RealtimePipeline
from src.realtime.service import RealtimeService

# bundle_path와 settings는 실행 가이드의 선택된 모델/설정에서 읽는다.
engine = InferenceEngine(bundle_path, model="lstm")
pipeline = RealtimePipeline(engine, settings)
service = RealtimeService(pipeline, queue_capacity=64)
stop = Event()
worker = Thread(target=service.run, args=(stop, handle_output))
worker.start()

# adapter가 해석한 sparse 관측을 넘긴다. queue.Full은 수신 측에서 처리한다.
service.submit(observation)

# 종료 시 수신을 멈추고 작업 스레드를 join한 뒤 recorder/출력 sink를 닫는다.
service.inbox.join()  # 수신을 멈춘 후 이미 받은 관측을 처리 완료한다.
stop.set()
worker.join()
```

`handle_output`은 정렬된 센서 행 또는 `record_type:STATUS`를 처리하는 callback이다. STATUS를 측정값이나 분류 정답으로 집계하지 않는다. `TimelineWriter.write`를 callback으로 연결할 수 있으며, 이벤트 recorder는 pipeline 생성 시 전달한다. 실제 UART/CAN 패킷 해석은 확인된 규격의 adapter가 담당한다.

CSV/Parquet replay는 관측 시각을 보존하는 오프라인 재생이다. 라이브 무응답 감시는 위 수신 루프에서 사용한다. replay에 호스트 timeout을 적용해 배속이나 PC 부하에 따라 학습 입력을 바꾸지 않는다. 소프트웨어 감시 스레드와 실제 MCU의 watchdog·최악 처리시간 검증은 별도다.

## 결과 파일과 회귀 범위

`artifacts/bugfix-20261013/`에 수정 전 파일, 테스트 XML, 실제 모델 CLI 재생과 로그를 저장한다. 타임라인 reader는 `summary.json`의 파일 목록을 사용하며, 전체 기록이 필요한 보고서·검증에서는 보관 중 일부가 제거됐다면 분석을 거부한다. 이전 단일 `timeline.jsonl` 결과도 읽을 수 있다.

기존 모델을 재학습하지 않고 마이크로초형 Parquet 7,200행을 실제 float32 LiteRT CLI에 입력해 저장된 Keras 결과와 입력 상태·경보 판단을 비교한다. 작은 검증용 파일 한도로 여러 세그먼트를 만들어 분할 읽기도 확인한다. 성공/입력 거부/설정 오류의 종료 코드는 별도 프로세스로 검사한다. 실제 결과는 `verification-2/cli-verification.json`, 전체 회귀는 `tests-final.xml`에 기록한다.

2026-10-12의 보고서·PPT에 있는 테스트 165개와 모델 성능은 당시 실행 기록이다. 이번 후속 테스트 개수는 별도 기록하며, 버그 수정으로 실제 낙뢰 성능이나 MCU 탑재를 새로 검증한 것은 아니다.

최종 검증 결과:

- 전체 **196개 테스트 통과**: 기존 165개 + 새 회귀 31개. 기존 Keras/NumPy 연동 DeprecationWarning 45건은 그대로 기록했다.
- 실제 LiteRT CLI의 마이크로초형 Parquet **7,200행**이 저장된 Keras 결과와 입력 상태·경보 판단에서 일치했다. 점수 최대 오차는 **1.1920929e-7**이었다.
- 검증용 2 MiB × 16개 한도로 타임라인이 **7개 파일**로 나뉘었다. 12,668,817바이트를 보관했으며, 기록 오류·보관 중 제거는 없었다. 기본 운용 설정은 32 MiB × 8개다.
- 실제 별도 프로세스의 종료 코드: 성공 **0**, 중복 입력 거부 **1**, 잘못된 설정 **2**.
- 모델을 재학습하지 않았으며 센서 위험 기준과 선택된 AI 임계값은 변경하지 않았다.

공식 API 확인: [Python datetime ISO 변환](https://docs.python.org/3.12/library/datetime.html#datetime.datetime.isoformat), [monotonic clock](https://docs.python.org/3.12/library/time.html#time.monotonic), [큐의 timeout과 용량](https://docs.python.org/3.12/library/queue.html#queue.Queue.get).
