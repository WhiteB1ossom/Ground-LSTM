# Windows 노트북에서 실행하기

**발표 시연용 ZIP을 받은 경우에는 먼저 루트의 [START_HERE.md](../START_HERE.md)를 따른다.** 노트북 Codex용 [인수인계 문서](../LAPTOP_CODEX_HANDOFF.md)와 `setup-laptop.cmd`가 설치·실제 모델 검증을 자동화한다. 아래 문서의 이전 모델 실행 예시는 과거 실험을 직접 옮길 때의 참고다.

현재 데스크탑의 학습된 모델을 복사해 노트북에서 바로 실행한다. 아래 순서는 일반적인 Intel/AMD Windows 64비트 노트북, Python 3.12, CPU 실행 기준이다. 모델 재학습은 필요하지 않다.

**새 열화 기준과 누적 서지 횟수를 반영한 서버 모델**은 [장비 점검·서지 서버 안내](equipment-server-20261015.md)의 실행 명령을 사용한다. 이 문서 아래의 7,200행 LSTM 실행 예시는 이전 합성 실험이다. 새 서버 실험을 옮길 때는 `artifacts/server-equipment-20261015/`와 `data/raw/equipment-server/server-equipment-20261015/`도 복사한다.

## 1. 데스크탑에서 프로젝트 복사

현재 `프로젝트` 폴더를 USB·외장 디스크·OneDrive로 노트북에 복사한다. 노트북의 예시 경로는 `C:\lightning-project`다. 압축해 옮겨도 되며 노트북에서 압축을 푼 뒤 실행한다. OneDrive로 옮길 때는 파일 다운로드 완료를 확인한다.

`.venv`, `.venv-ml`, `.pytest_cache`, `__pycache__`, `lightning_risk_pipeline.egg-info`는 제외할 수 있다. 나머지는 폴더 구조를 유지해 복사한다. 특히 `artifacts`와 `data`는 `.gitignore`에 있으므로 Git으로 코드만 복사하면 모델과 데이터가 빠진다.

최소한 아래 파일은 있어야 한다.

- `src/`, `configs/`, `pyproject.toml`, `requirements-integration-lock.txt`
- `artifacts/integrated-20261012/bundle-final/` 전체: 모델·scaler·특징 순서·무결성 정보
- `artifacts/integrated-20261012/replay-selected.yaml`: 선택된 경보 정책
- `artifacts/integrated-20261012/calibrated-3/inputs/heldout.synthetic.csv`: 합성 Test 7,200행

학습·평가와 기존 결과까지 이어서 작업하려면 `scripts`, `tests`, `docs`, `data`, `artifacts`, `output`도 함께 보관한다. 가상환경은 노트북에서 다시 만든다. Python 공식 문서도 가상환경을 복사하는 대신 새 위치에서 재생성하도록 안내한다. [Python venv 문서](https://docs.python.org/3.12/library/venv.html)

## 2. 노트북에 Python 설치

Python **3.12 64비트**와 Python Launcher를 설치한다. Windows 설치 파일이 필요한 경우 [Python 3.12.10 공식 다운로드](https://www.python.org/downloads/release/python-31210/)의 `Windows installer (64-bit)`를 사용할 수 있다. 설치 화면에서 launcher와 PATH 등록 항목을 확인한다. 이미 3.12가 설치돼 있으면 재설치하지 않는다.

TensorFlow를 위한 Microsoft Visual C++ Redistributable x64도 필요하다. Visual Studio 전체 설치와는 다르다. [TensorFlow 공식 설치 요구사항](https://www.tensorflow.org/install/pip)의 Windows 항목에 있는 Microsoft 다운로드 링크를 사용한다.

노트북에서 PowerShell을 열고 실제 복사 경로로 이동한다.

```powershell
cd C:\lightning-project
py -3.12 --version
py -3.12 -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install -r requirements-integration-lock.txt
.\.venv-ml\Scripts\python.exe -m pip install --no-deps -e .
.\.venv-ml\Scripts\python.exe -m pip check
```

설치 중 인터넷 연결이 필요하다. 각 명령이 성공한 뒤 다음 명령을 실행한다. 다른 컴퓨터에서 복사한 `.venv-ml`은 사용하지 않는다. 위 명령은 가상환경을 활성화하지 않고 Python을 직접 지정하므로 `Activate.ps1` 실행 정책을 바꿀 필요가 없다.

## 3. 학습된 LSTM 실행

프로젝트 폴더의 PowerShell에서 다음을 실행한다.

```powershell
$out = Join-Path '.\artifacts' ('laptop-replay-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))

.\.venv-ml\Scripts\python.exe -m src.realtime.replay `
  --input .\artifacts\integrated-20261012\calibrated-3\inputs\heldout.synthetic.csv `
  --bundle .\artifacts\integrated-20261012\bundle-final `
  --model lstm `
  --config .\artifacts\integrated-20261012\replay-selected.yaml `
  --speed max --output $out

$LASTEXITCODE
Get-Content (Join-Path $out 'summary.json') -Raw -Encoding UTF8
```

이 명령은 학습된 Keras LSTM으로 입력 → 전처리 → 링 버퍼 → 추론 → 경보 판단 → 이벤트 저장을 실행한다. 별도의 GUI 창은 열지 않으며 콘솔과 결과 파일로 확인한다. 합성 데이터 재생이므로 실제 센서나 MCU 연결은 필요하지 않다.

정상 완료 기준은 종료 코드 `0`, `summary.json`의 `status:SUCCESS`, `observations:7200`, `aligned_rows:7200`이다. 출력 폴더에는 `summary.json`, `timeline*.jsonl`, `events/`가 생긴다. 실제 시간 간격으로 시연하려면 `--speed max`를 `--speed 1`로 바꾼다. 이 데이터의 전체 재생에는 그만큼 실제 대기시간이 필요하다.

현재 `run.json`과 LiteRT `export-report.json`에는 데스크탑의 절대경로가 기록돼 있다. 노트북에서는 이전 가이드의 `$run.stages...path`를 그대로 사용하지 말고 위 상대경로 명령을 사용한다. LiteRT는 경로를 무결성 정보와 대조하므로 `.tflite` 경로만 바꾸면 출처 검사에 실패할 수 있다. 위 Keras 실행은 그 export 보고서를 사용하지 않으며 모델·scaler·경보 정책은 그대로 적용한다. 이전 기록이나 모델 manifest를 일괄 치환하지 않는다.

## 4. 노트북에서 추가 작업

VS Code를 사용하면 프로젝트 폴더를 열고 Python 인터프리터로 `.venv-ml\Scripts\python.exe`를 선택한다. VS Code 자체는 실행 필수 조건이 아니다.

전체 테스트는 다음과 같다.

```powershell
.\.venv-ml\Scripts\python.exe -m pytest -q
```

새로운 학습·변환·평가를 모두 수행하려면 [통합 실행 가이드](integration-usage.md)의 전체 실행 절차를 사용한다. 이 절차의 C++ host 검증에는 Visual Studio Build Tools의 MSVC가 추가로 필요하다. 단순 LSTM 재생에는 C++ 컴파일러가 필요하지 않다. 복사한 과거 run에 바로 `resume`을 실행하기보다 새 run을 생성해 노트북 경로의 결과를 남긴다.

현재 Windows CPU 실행은 GPU 설치 없이 진행한다. TensorFlow 2.11 이후 Windows native GPU 지원 조건은 별도로 다르며 [TensorFlow 공식 문서](https://www.tensorflow.org/install/pip)를 따른다. 데스크탑에서 보던 oneDNN·CPU·GPU 미사용 안내만으로 실행 실패라고 판단하지 않는다. 마지막 traceback, 종료 코드와 `summary.json`을 확인한다.

노트북의 CPU·메모리·Windows 환경은 아직 직접 검증하지 않았다. `No matching distribution`이면 Python 3.12·64비트·회사/학교 패키지 서버 설정을, DLL 오류이면 Visual C++ 런타임을 확인한다. ARM 기반 Windows 노트북은 이 x64 검증 환경과 달라 별도 호환성 확인이 필요하다.

2026-10-15 데스크탑 검증에서는 소스·bundle·입력을 원래 경로와 다른 폴더로 복사한 뒤 위 상대경로 Keras 명령으로 7,200행을 처리해 `SUCCESS`와 저장 종료 완료를 확인했다. 노트북의 새 환경 설치나 실제 노트북 하드웨어를 시험한 것은 아니다. 결과는 `artifacts/laptop-transfer-check-20261015/verification.json`에 보관한다.
