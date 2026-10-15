# 2026-10-14 경계 상황 재점검

이번에는 입력 소유권, 전체 시퀀스의 유효성, 파일 형식·헤더, 반복 처리와 정상 종료를 점검했다. 다음 오류를 재현하고 수정했다. 학습 모델·센서 기준값·선택한 경보 정책은 유지한다.

## 1. 현재 측정과 전체 창의 유효성 구분

과거 오류 행이 포함되어 `input_status:INVALID_WINDOW`인 창에서도 `window_valid:true`가 표시됐다. 이전 값은 현재 측정 행의 유효성만 나타냈기 때문이다. 준비 중인 짧은 창에서도 동일한 표시 문제가 있었다.

새 로그는 `sample_valid`로 현재 행, `window_valid`로 전체 입력 창을 구분한다. 이전 오류 행이 남아 있으면 현재 행이 정상이더라도 창은 유효하지 않다. 추론 사이의 stride 대기 시점에도 창의 모든 행과 timestamp 간격을 확인한다. 추론 실행 자체가 실패한 경우에는 입력 창이 유효할 수 있지만 `available:false`로 구분한다.

예를 들어 현재 측정은 정상이고 이전 측정 하나가 오류이면 `sample_valid:true`, `window_valid:false`, `available:false`다. 이전 저장 파일은 수정하지 않았다. 과거 로그의 상태를 해석할 때는 `input_status`와 `available`도 확인한다.

## 2. 수신 대기 입력과 보관 입력의 복사

`RealtimeService.submit()`의 기존 얕은 복사에서는 수신자가 중첩 metadata를 변경하면 queue에 대기 중인 데이터도 달라졌다. 비정렬 입력을 `feed()`한 뒤 다음 샘플을 기다리는 동안에도 같은 참조 문제가 있었다.

표준 라이브러리 `deepcopy`로 수신 queue와 파이프라인의 보관 입력을 각각 분리한다. 전처리 전에는 JSON 변환을 사용하지 않는다. 실제 NaN은 오류 측정이고 None은 새 측정 없음이라는 기존 차이를 유지해야 하기 때문이다. [Python 공식 copy 문서](https://docs.python.org/3.12/library/copy.html)를 확인했다.

## 3. 파일 형식과 구조 검사의 일관성

대문자 `.PARQUET` 입력이 CSV로 읽혀 `UnicodeDecodeError`가 발생했다. 이제 확장자의 대소문자를 구분하지 않고 CSV/Parquet를 선택한다. 다른 확장자는 명시적인 입력 오류로 거부한다.

두 형식에 같은 헤더 검사를 적용해 timestamp 누락, 활성 센서 누락, 중복·빈 열 이름을 거부한다. Parquet에서는 Arrow의 최상위 열 이름을 사용한다. CSV 따옴표 문법 오류도 검사하고 `csv.Error`를 `ValueError`로 전달해 CLI의 입력 실패 처리를 따른다. 승인된 정상 입력을 임의로 정렬·채우거나 원본 파일을 수정하지 않는다.

공식 API는 [Python CSV 문서](https://docs.python.org/3.12/library/csv.html), [Arrow ParquetFile 문서](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetFile.html)를 확인했다.

## 4. 전 기록이 0초인 이벤트의 완료 표시

전 기록이 필요하지 않은 `pre_seconds:0`에서도 `pre_history_complete:false`로 표시되던 오류를 수정했다. 요청된 전 구간이 없으면 전 기록은 완료로 표시한다. 실제 pre/post 시간 설정은 변경하지 않았다.

## 검증

- 새 회귀 시험: 확장자 대소문자, Parquet 헤더 오류, CSV 문법·행 길이 오류, 지원하지 않는 형식, 대기/보관 입력의 중첩 변경, NaN/None 의미, 준비·오류·복구 창 표시, 추론 실패와 창 유효성 분리, stride 대기 중 시간 누락, 0초 전 기록 표시.
- 오류 입력을 주기적으로 섞은 **5,000회 처리**에서 창 유효성을 독립적인 최근 입력 목록과 비교했다. 링 배열 할당과 버퍼 한도 유지, 원본 metadata 분리, 저장 완료 후 worker 종료와 queue 정리를 확인했다. 이는 가상 센서 시간의 반복 처리 시험이며 실제 장치 장시간 시험은 아니다.
- 새 회귀 시험 21개를 포함해 관련 테스트 **131개**, 전체 테스트 **255개**가 통과했다. 전체 실행 시간은 58.89초이며 기존 Keras/NumPy DeprecationWarning 45개가 남는다.
- 실제 선택한 float32 LiteRT 모델로 typed Parquet **7,200행**을 재생했다. 이전 Keras 기록과 특징·입력 상태·가용 여부·경보 판단이 일치했고 최대 점수 차이는 **1.1920928955078125e-7**이다. 이벤트 8개의 원본 기록 568개도 시간 범위와 일치했다.
- 기존 모델·bundle·export·선택 설정·발표자료 등의 **98개 파일 해시** 비교 결과는 `verification.json`에 보관한다. 모델을 재학습하거나 경보 기준을 변경하지 않았다.
- 증거: `artifacts/review-20261014/tests-focused.xml`, `tests-final.xml`, `verification/runtime-verification.json`, `verification.json`.
- 기존 코드 snapshot은 같은 폴더의 `baseline/`, 모델·bundle·export·선택 설정·발표자료 등의 98개 파일 해시는 `protected-hashes.json`에 보관한다.

이번 검증은 PC 소프트웨어의 위 범위에 해당한다. 실제 MCU 처리 기한·전체 RAM/Flash·wire decoder·실측 낙뢰 성능은 별도 검증 항목이다.
