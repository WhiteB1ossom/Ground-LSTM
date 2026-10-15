# 2026-10-13 추가 실시간 버그 수정

추가 점검에서 재현한 네 가지 오류를 수정했다. 학습된 모델, scaler, 센서 기준값, 선택된 AI 임계값과 경보 정책은 유지한다. 이번 변경 범위는 PC 실시간 추론·평가·이벤트 기록 경로다.

## 1. TensorFlow 추론 오류

Keras 실행 중 발생하는 `InternalError`, `ResourceExhaustedError` 등 `tf.errors.OpError`를 추론 adapter에서 원인을 포함한 `RuntimeError`로 변환한다. 기존 실시간 파이프라인은 이를 `INFERENCE_ERROR / UNAVAILABLE`로 기록하고 기존 경보를 유지한다. 실패한 점수는 재사용하지 않으며 다음 성공한 추론에서 복구한다. 예상하지 못한 프로그래밍 오류는 그대로 전파한다.

예외 범위는 [TensorFlow의 공식 OpError 문서](https://www.tensorflow.org/api_docs/python/tf/errors/OpError)와 설치된 TensorFlow 2.21.0 구현을 확인했다. 모델 초기화·입력 계약 검사는 기존 동작을 유지한다.

## 2. STATUS와 센서 지표 분리

`StreamMetrics.consume()`는 `record_type:STATUS`를 센서 필드 접근 전에 제외한다. 따라서 `INPUT_TIMEOUT`은 측정 시간·coverage·FP/FN·위험 구간에 들어가지 않고, 센서 필드가 없는 `INPUT_REJECTED`도 평가를 중단시키지 않는다. STATUS는 타임라인에 그대로 보관한다. 실제 센서 행의 필수 필드가 빠진 오류는 숨기지 않는다.

## 3. 정렬 격자 사이의 원본 측정 보존

기존 `raw_observation`은 측정 timestamp가 정렬 timestamp와 정확히 같을 때만 기록됐다. 이제 정렬 행의 이 필드는 **가장 최근에 수신한 원본 행**을 담으며, 내부 원본 timestamp를 유지한다. 같은 원본이 여러 정렬 행에서 참조될 수 있으므로 이 필드의 개수는 수신 측정 개수가 아니다.

별도로 `EventRecorder.observe()`가 승인된 원본 측정을 정렬 전에 보관한다. 이벤트 JSON의 `raw_observations`에는 다음 구조로 전/후 구간의 원본을 수신 순서대로 기록한다.

```json
{"timestamp_ns": 1767225600050000000, "raw_observation": {"timestamp": "2026-01-01T00:00:00.050000+00:00", "v": 0.9}}
```

한 정렬 간격 안의 여러 측정과 마지막 정렬 시점 이후의 EOF 측정도, 해당 이벤트 구간 안에 있으면 보존한다. 이 보관은 모델 입력·정답·시퀀스 생성에 사용하지 않는다. 세션 변경과 입력 timeout에서는 기존 이벤트를 미완성 사유와 함께 저장하고 원본 이력을 분리한다.

원본 이력 기본 한도는 1,024개이고 이벤트별 한도는 4,096개다. `replay.raw_history_capacity`, `replay.max_raw_observations_per_event`로 조정한다. 한도를 넘으면 summary에 `raw_history_dropped` / `raw_event_dropped`, 이벤트에 `raw_observations_truncated` / `dropped_raw_observations`를 기록하며 replay 결과는 `DEGRADED`다. `complete`는 기존처럼 post-event 시간 구간 완료 여부이고, 원본 누락 여부는 별도 필드로 확인한다.

전체 수신 원본의 영구 저장소는 아니다. 경보가 발생한 전/후 구간을 보관하는 기능이며, 전체 원본 CSV/Parquet는 기존 수집 경로에서 보존한다. 입력률이 커지면 원본 이력 한도도 함께 검토해야 한다.

## 4. 저장 실패 후 임시 파일 정리

현재 저장 작업에서 직접 생성한 `.partial`만 실패 후 삭제한다. 이미 있던 파일은 보존한다. 삭제도 실패하면 `storage_disabled:true`, `cleanup_error_count`와 상세 오류를 기록하고 추가 파일 생성을 중단한다. 성공한 이벤트 개수 제한과 비동기 writer는 유지한다. 파일 삭제 동작은 [Python pathlib 문서](https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.unlink)를 확인했다.

## 검증

- 추가 회귀 시험: TensorFlow 세 종류의 실행 오류와 복구, 예상 밖 오류 전파, STATUS 집계 제외, 밀집·비정렬 측정과 EOF 보존, 세션 분리, 원본 보관 한도, 임시 파일 정리·삭제 실패·기존 파일 보호.
- 추가 회귀 테스트 25개를 포함해 관련 테스트 82개, 전체 테스트 **221개**가 통과했다. 전체 실행 시간은 54.51초이며 기존 Keras/NumPy DeprecationWarning 45개가 남는다.
- 실제 선택 모델의 float32 LiteRT CLI로 typed Parquet **7,200행**을 재생했다. 종료 코드 0이며 기존 Keras 기록과 특징·입력 상태·가용 여부·경보 판단이 모두 일치했다. 최대 점수 차이는 **1.1920928955078125e-7**이다.
- 저장된 **8개 이벤트의 원본 568개 기록**이 각 이벤트의 전/후 구간에 해당하는 입력 timestamp 목록과 정확히 일치했다. 원본 보관 한도 초과와 writer 오류는 없었다.
- 실제 선택된 Keras 모델의 추론 실행부에 `InternalError`를 주입해 `UNAVAILABLE`, 기존 경보 유지, 다음 추론 복구를 확인했다.
- 학습 모델은 재학습하지 않았다. 기존 모델·bundle·export·발표자료·선택 설정 등의 98개 파일 해시를 비교한 결과는 `verification.json`에 기록한다.
- 증거: `artifacts/bugfix-20261013-extra/tests-focused.xml`, `tests-final.xml`, `verification/runtime-verification.json`.
- 기존 코드 snapshot: 같은 디렉터리의 `baseline/`. 기존 모델·발표자료 등의 해시: `protected-hashes.json`.

실제 MCU 탑재와 실측 낙뢰 성능은 기존처럼 별도 검증 항목이다.
