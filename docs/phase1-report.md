# PHASE 1 완료 보고서

검증일: 2026-10-03 (Asia/Seoul). 현재 작업은 최초 요청의 PHASE 1 범위입니다.

## 1. 구현 파일

- 프로젝트/설치: `pyproject.toml`, `requirements.txt`, `requirements-lock.txt`, `.gitignore`
- 설정: `configs/sensors.yaml`, `preprocessing.yaml`, `model.yaml`, `realtime.yaml`, `target_mcu.yaml`, `synthetic.yaml`
- 설정 로딩/검증: `src/utils/config.py`
- 입력 계약: `src/data/schema.py`
- CSV/Parquet 탐색·원본 로딩: `src/data/loader.py`
- 품질검사/보고서: `src/data/quality.py`, `report.py`, `inspect.py`
- 합성 데이터: `src/data/synthetic.py`, `scripts/generate_synthetic_data.py`
- 테스트: `tests/conftest.py`, `test_data_pipeline.py`, `test_edge_cases.py`
- 사용/후속 architecture: `README.md`
- 구조: 요청의 `src` 하위 패키지 및 `data`, `artifacts` 하위 디렉터리. 후속 패키지는 미구현임을 명시한 skeleton.

실행 산출물: 정상 CSV/Parquet와 metadata는 `data/raw`, 오류 CSV와 metadata는 `data/interim`, JSON/Markdown 품질 보고서 및 `phase1-verification.json`은 `artifacts/reports`에 있습니다.

## 2. 핵심 설계 이유

wide sparse 입력에서 빈 셀은 비관측일 수 있으므로 전체 행 간격과 센서별 관측 간격을 구분했습니다. 아직 forward fill·리샘플링을 하지 않아 원본 획득 시점을 보존합니다. source가 다른 고속 surge와 모니터링을 섞지 않으며 동일 timestamp도 장치별로 검사합니다.

범위 초과는 검토(reason code)로만 표시합니다. 급격한 변화를 지우지 않고 명시적 입력 오류와 물리적 극단값의 가능성을 구분합니다. raw 파일·행 순서·센서값을 변경하지 않고 SHA-256과 설정 snapshot으로 보고서 출처를 남깁니다.

미확정 단위·범위·위험 threshold·staleness·MCU 사양은 null입니다. 합성 상태와 이벤트는 임의 단위의 software fixture이며 ground_truth는 모두 UNLABELED입니다. 품질검사 성공은 물리적 타당성·학습 승인·MCU 탑재 가능성을 보장하지 않습니다.

## 3. 실행 방법

프로젝트 루트 PowerShell:

```powershell
.\.venv\Scripts\python -m src.data.inspect --config configs/preprocessing.yaml
.\.venv\Scripts\python -m pytest -q
```

새 합성 fixture:

```powershell
.\.venv\Scripts\python -m scripts.generate_synthetic_data --output data/raw/new-demo.synthetic.csv
```

기존 output은 보호하므로 재실행 시 새 경로를 사용합니다. 설치·설정·전체 CLI 옵션은 README에 있습니다. 원본이 표준 스키마를 따르면 `data/raw` 파일을 자동 탐색합니다.

## 4. 실제 검증 결과

- pytest: **50 passed, 0 failed** (최종 실행 3.75초).
- `compileall`: `src`, `scripts`, `tests` 통과.
- `pip check`: No broken requirements found.
- editable 설치 성공, 로컬 `.venv`에서 검증.
- 정상 CSV 및 Parquet: 각각 1,801행, UNLABELED, synthetic=true, invalid=false. 보고서 JSON/Markdown 생성 성공.
- 정상 fixture의 빈 셀 12,219개는 다중 주기 비관측입니다. 센서별 관측 간격은 설정된 nominal 주기와 일치하며 간격 편차 reason이 발생하지 않았습니다.
- 오류 fixture: timestamp 파싱/중복/역전, NaN/Inf/비수치값, sensor/communication 오류를 보고하고 CLI 종료 코드 1 반환. 예상된 데이터 검출 결과이며 테스트 실패가 아닙니다.
- 원본 바이트·값·순서 보존, CSV/Parquet 왕복, DST ambiguity, config 오류, malformed CSV, source 격리, disabled 센서, flatline 공백, 재현성·덮어쓰기 보호를 테스트.

구체적인 버전 및 보고서 reason counts는 `artifacts/reports/phase1-verification.json`에 기록했습니다. 환경별 정확한 dependency pin은 `requirements-lock.txt`에 있습니다.

## 5. 남은 TODO

기업 확인: 실제 파일의 단위/컬럼/관측 의미, 수집 상태 코드, timestamp timezone, label/event 계약, sensor expected range/threshold/max_staleness, 습도·외기온도 주기, 별도 surge schema와 MCU 사양.

PHASE 2: 동일 causal transform을 공유하는 aligner, missing/stale 정책, feature 순서 artifact, split-before-window, event 격리·purge gap, train-only scaler 및 시퀀스 생성. 아직 관련 학습 데이터나 모델은 생성하지 않았습니다.

PHASE 3 이후: 실제 label 기반 baseline/LSTM 평가, 경량화/TFLite 및 MCU operator/resource 검증, advisory 실시간 pipeline·고정 ring buffer·event recorder, CSV replay와 E2E. 각 Phase에서 요구된 검증을 추가합니다.

현재 검사는 batch 방식으로 전체 입력과 issue를 메모리에 적재합니다. 대용량 surge와 장치별 비표준/복합 상태 정보는 후속 source adapter가 필요합니다.
