# Windows 노트북 Codex 인수인계

사용자가 이 문서를 읽고 설정을 진행해 달라고 요청한 경우, 아래 절차로 실제 실행을 확인한다. 목표는 **기존 학습 모델을 이용한 발표 시연**이다. 이 문서만으로 이전 채팅에 접근할 필요는 없다.

## 목표와 현재 상태

- Windows Intel/AMD x64, Python 3.12 x64, CPU 실행을 기준으로 준비했다. 먼저 실제 노트북의 OS·CPU 아키텍처·Python 설치 상태를 확인한다. ARM Windows이면 x64 호환성을 확인하고 현재 검증 범위와 구분한다.
- 학습된 모델은 장비 점검과 서지 활동을 구분하는 LSTM 두 개다. 입력은 센서 10개, 특징 39개, 창 64개 시점, 추론 stride 10이다. 링 버퍼 용량은 114개 시점이다.
- 최신 실행은 `server-equipment-20261015`다. 이전 `integrated-20261012` 모델을 실행 대상으로 사용하지 않는다.
- 모델 재학습·재튜닝·TFLite 변환·CUDA 설치 없이 동작한다. 설치 문제를 해결하려고 모델 manifest·해시·임계값·학습 결과를 수정하지 않는다.
- 입력은 합성 Test 데이터다. 실제 장비 연결·실제 낙뢰 확정·현장 고장 성능 검증은 이번 완료 조건에 포함하지 않는다.

## 먼저 읽을 파일과 경로

모든 명령은 이 프로젝트 루트에서 실행한다. 데스크탑의 사용자 이름이나 절대경로를 가져오지 않는다.

| 용도 | 경로 |
|---|---|
| 설치 자동화 | `setup-laptop.cmd`, `scripts/setup_laptop.py` |
| 고정 패키지 버전 | `requirements-integration-lock.txt` |
| 모델·데이터 실제 검증 | `scripts/verify_laptop.py` |
| 시연 실행 | `run-demo.cmd`, `src/realtime/demo.py` |
| 모델 연결 목록 | `artifacts/server-equipment-20261015/server-models.json` |
| 실제 모델·scaler·무결성 정보 | 같은 폴더의 `degradation/bundle/`, `surge/bundle/` |
| 모델별 경보 정책 | 같은 폴더의 `degradation/replay-selected.yaml`, `surge/replay-selected.yaml` |
| Test 입력 | `data/raw/equipment-server/server-equipment-20261015/heldout.synthetic.csv` |
| ZIP 파일별 SHA256 | `TRANSFER-MANIFEST.json` |
| 시연 순서·화면 해석 | `docs/presentation-demo.md` |

## 환경 설치

1. Python 3.12 x64 설치 여부를 확인한다. `py -3.12 --version`과 인터프리터의 버전·64비트 여부를 확인한다. 사용 가능한 다른 버전으로 임의 대체하지 않는다.
2. Python이 없으면 Python 공식 배포 경로에서 3.12 x64와 launcher를 준비한다. 명령행 설치나 사용 가능한 패키지 관리자를 활용할 수 있다. 실제 설치 방법과 배포 출처를 확인하고 진행하며 시스템 설치가 요구하는 UAC는 사용자에게 맡긴다. Python 공식 다운로드: https://www.python.org/downloads/windows/
3. TensorFlow DLL 오류가 나면 Microsoft Visual C++ Redistributable x64 설치 여부를 확인하고 공식 런타임으로 해결한다. Visual Studio 전체나 GPU 도구는 시연 필수 조건이 아니다. 공식 안내: https://www.tensorflow.org/install/pip 및 https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
4. 프로젝트 루트에서 다음을 실행한다. CLI 작업에서는 `--non-interactive`를 사용해 CMD의 마지막 대기를 생략한다.

```powershell
.\setup-laptop.cmd --non-interactive
```

직접 Python 실행 파일을 확인했다면 같은 설치를 다음 명령으로 실행할 수 있다.

```powershell
py -3.12 -m scripts.setup_laptop --non-interactive
```

설치 스크립트는 ZIP 무결성 확인 → `.venv-ml` 생성 → 고정 버전 설치 → editable 프로젝트 설치 → `pip check` → 실제 LSTM 검증을 순서대로 실행한다. 전역 Python이나 시스템의 다른 환경을 수정하지 않는다. 기존 `.venv-ml`이 정상적이면 재사용한다. 잘못된 기존 환경은 자동 삭제하지 않으므로 원인을 확인한 뒤 보존하고 새 작업 폴더를 사용한다.

설치가 중간에 끊겼다면 원인을 해결한 뒤 같은 명령으로 다시 진행한다. 패키지 버전 없음·프록시·인증서·네트워크 오류를 숨기거나 무작정 lock 파일의 버전을 풀지 않는다. pip가 출력한 원인을 확인하고 공식 지원·설치 조건과 대조한다. 기존 설치 환경 확인만 다시 하려면 다음 명령을 사용한다.

```powershell
.\setup-laptop.cmd --skip-install
```

가상환경은 노트북에서 새로 만든다. 활성화는 필요 없고 `.venv-ml\Scripts\python.exe`를 직접 사용한다. 시스템 PowerShell 실행 정책을 바꾸지 않는다. [Python 공식 venv 안내](https://docs.python.org/3.12/library/venv.html)

## 검증과 시연 실행

설치의 마지막 단계는 실제 두 Keras 모델로 `발열 + 서지` 획득 세션 전체를 재생한다. 약 1,800행을 처리하고, 각 작업에서 실제 추론 174회·링 버퍼 덮어쓰기·두 경보 동시 활성 구간을 확인한다. 결과는 새 `artifacts/laptop-check/<실행시각-임의번호>/laptop-verification.json`과 타임라인에 저장한다. `status: SUCCESS`를 확인한다. 생성된 JSON 경로를 사용자에게 알려준다.

시연 서버는 프로젝트 루트에서 실행한다.

```powershell
.\.venv-ml\Scripts\python.exe -m src.realtime.demo --open
```

Codex에서 백그라운드로 유지하려면 Python 실행 파일을 명시하고 `Start-Process -WindowStyle Hidden`으로 실행한 뒤 stdout/stderr 로그와 PID를 새 결과 폴더에 기록한다. 다른 프로세스가 8765 포트를 쓰면 종료하지 말고 소유 프로세스를 확인한다. 필요하면 `--port 8766`을 사용한다. 기존 프로젝트 서버가 이미 정상 동작한다면 해당 주소를 사용할 수 있다.

1. `http://127.0.0.1:8765/api/state`에서 모델 로딩이 끝나 `status: READY`인지 확인한다. `ERROR`이면 메시지와 로그를 해결한다. 기존 실행 중인 서버는 RUNNING/PAUSED/FINISHED일 수 있다.
2. 가능하면 브라우저에서 같은 주소의 `/`를 열고 `발열 + 서지` → `처음부터 재생`을 눌러 센서값·버퍼·실제 모델 점수·경보가 표시되는 것을 확인한다. 브라우저 제어가 없으면 API 확인과 실제 모델 검증 결과를 구분해 보고하고 사용자가 열 주소를 제공한다.
3. 시연 종료는 직접 연 실행 창에서 `Ctrl+C`를 사용한다. Codex가 만든 백그라운드 프로세스를 종료할 때는 기록한 PID와 소유 프로세스를 먼저 확인한다.

oneDNN·CPU 최적화·Windows GPU 미지원 안내만으로 실패로 판단하지 않는다. 실제 traceback·종료 코드·`laptop-verification.json`·API 상태를 확인한다.

## 프로젝트 의미와 작업 범위

현재 점검 조건은 대지전위 A/B ≥ 2V, 누설전류 ≥ 2mA(입력 단위 0.002A), 제한소자 A/B/C ≥ 45℃, 습도 ≥ 70%다. 제조사 인증 고장 판정 기준으로 주장하지 않는다. 외기온도 25℃는 참조값, 입력전압 220V는 이번 합성 실험 참조값이다. 누적 서지 감소는 리셋으로 구분하며 낙뢰로 확정하지 않는다. 실제 장비를 제어하지 않는다.

ZIP에는 코드·설정·테스트·문서·기존 발표자료와 최신 실행용 모델·Test 입력을 포함했다. 과거 실행 전체·학습 데이터 전체·가상환경은 제외했다. 이전 문서·발표자료의 과거 run 경로가 없어도 이번 설치 실패를 뜻하지 않는다. 추가 학습이 필요해지면 새 출력 폴더로 데이터 생성부터 진행하며 현재 모델을 덮어쓰지 않는다.

완료 시 실제 확인한 Python/TensorFlow 버전, `pip check`, 실제 모델 검증 결과, 브라우저 주소와 실행 방법을 짧게 보고한다. 설치·검증 없이 실행 완료라고 판단하지 않는다.
