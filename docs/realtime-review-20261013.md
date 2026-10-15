# 2026-10-13 재점검과 추가 보완

이전 수정 후 경계 상황을 다시 점검해 다음 세 가지 오류를 재현하고 수정했다. 학습 모델과 선택된 기준값·경보 정책은 유지한다.

## 1. 반환 결과와 저장 기록의 참조 공유

수정 전에는 `RealtimePipeline.feed()`가 반환한 행과 recorder의 이벤트 이력이 같은 dict/list를 참조했다. 반환된 `processed_values`를 9,999로 바꾸자 저장된 이벤트의 값도 9,999가 됐다. 비동기 writer가 대기하는 동안에도 동일한 문제가 발생할 수 있었다.

`EventRecorder.consume()`에서 프로젝트의 JSON 변환 함수로 중첩 값까지 복사한 snapshot을 보관하도록 변경했다. constructor로 전달받은 metadata도 복사한다. UI 표시용 값이나 반환 결과를 수정해도 원본 이벤트 기록이 바뀌지 않는다.

## 2. 실시간 출력 실패 보고

`TimelineWriter.write()`가 `False`를 반환해도 `RealtimeService.run()`은 기존 수신 개수만 반환했다. 실제 실패한 쓰기 3개가 서비스 결과에 표시되지 않는 것을 확인했다.

이제 callback이 명시적으로 `False`를 반환하면 `output_failure_count`를 증가시킨다. callback이 값을 반환하지 않는 경우(`None`)는 정상으로 처리한다. 추론·전처리 오류는 `processing_failure_count`, 종료 시 대기 중인 입력은 `pending_observations`로 보고한다. 실패·입력 거부·queue overflow·timeout·미처리 입력이 있으면 서비스 결과는 `DEGRADED`다.

출력 callback이 던진 예외는 기존처럼 전파한다. callback이 내부에서 실패를 처리했다면 `False`를 반환해야 집계된다. 서비스 결과는 수신·처리·callback 결과의 집계이며, 비동기 이벤트 writer의 최종 저장 결과는 worker 종료 후 `recorder.close()`의 보고서도 확인한다.

## 3. 수치 overflow 후 입력 처리 정지

유한한 숫자라도 float32 모델 입력으로 표현할 수 없는 값이 있을 수 있다. 예를 들어 1e300이 들어오면 scaler에서 실패했고, 이미 진행된 시간 상태 때문에 이후 정상 입력에서도 `Sample timestamps must strictly increase`가 반복됐다.

scaler의 숫자 연산과 float32 변환에서 overflow/invalid/divide 오류를 명시적인 `ScalingOverflowError`로 변환한다. 이 예외는 기존 `ValueError` 계열을 유지한다. 오류 정책은 연산 구간에만 적용하고 이전 NumPy 정책을 복원한다. [NumPy 공식 errstate 문서](https://numpy.org/doc/stable/reference/generated/numpy.errstate.html)를 확인했다.

실시간 파이프라인은 해당 행을 `PREPROCESSING_ERROR / UNAVAILABLE`로 출력하고 링 버퍼에 `valid:false`로 넣어 시간 진행을 유지한다. 고정 크기 자리에는 유한한 0을 넣지만, 이 행이 포함된 창은 추론하지 않는다. 기존 경보는 유지하고, 정상 입력만으로 새 유효 창을 확보하면 복구한다. 입력 값을 임의로 센서 기준값에 맞춰 잘라내거나 위험 정답을 만들지 않는다.

replay는 `preprocessing_failure_count`를 별도로 기록하고 숫자 오류가 있으면 `DEGRADED`로 보고한다. 이후 정상 행은 계속 처리한다. feature 순서나 행렬 shape 같은 계약 오류는 이 복구 처리로 숨기지 않는다.

## 검증 자료

- 추가 회귀 시험: 반환된 pre/post 행 변경, 비동기 writer 대기 중 변경, metadata 변경, 실제 타임라인 쓰기 실패, STATUS 쓰기 실패, callback의 None 반환, 종료 시 대기 입력, 양·음 overflow 후 복구, NumPy 오류 정책 복원, 계약 오류 전파, 실시간/replay 오류 집계.
- 새 회귀 테스트 13개를 포함해 관련 테스트 **95개**, 전체 테스트 **234개**가 통과했다. 전체 실행 시간은 62.82초이며 기존 Keras/NumPy DeprecationWarning 45개가 남는다.
- 실제 선택 모델의 float32 LiteRT CLI로 typed Parquet **7,200행**을 재생했다. 기존 Keras 기록과 특징·입력 상태·가용 여부·경보 판단이 모두 일치했고 최대 점수 차이는 **1.1920928955078125e-7**이다. 저장된 이벤트 8개, 원본 기록 568개의 시간 범위도 검증했다.
- 기존 모델·bundle·export·선택 설정·발표자료 등의 **98개 파일 해시**는 `protected-hashes.json`과 비교하며, 종합 확인 결과는 `verification.json`에 저장한다.
- 증거 파일은 `artifacts/bugfix-20261013-review/tests-final.xml`, `verification/runtime-verification.json`이다.
- 기존 코드 snapshot은 같은 폴더의 `baseline/`, 보호한 98개 파일의 해시는 `protected-hashes.json`에 보관한다.

검증 범위는 PC 소프트웨어다. 실제 MCU 최악 처리시간·전체 자원·통신·실측 낙뢰 성능 검증은 남아 있다.
