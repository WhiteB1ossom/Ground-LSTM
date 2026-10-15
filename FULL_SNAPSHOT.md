# 전체 프로젝트 스냅샷 (master)

이 브랜치는 요청에 따라 소스뿐 아니라 데이터, 학습 모델, 실험 결과, 발표·보고서 작업 자료,
`.venv`, `.venv-ml`, 숨김 파일과 캐시까지 포함합니다. `.git`은 Git 자체 관리 정보입니다.
원본 바이트 보존을 위해 줄바꿈 자동 변환을 끄고, 10 MiB 이상 파일은 Git LFS로 저장합니다.

노트북에서 전체 파일 받기:

```powershell
git lfs install
git clone --branch master https://github.com/WhiteB1ossom/Ground-LSTM.git
cd Ground-LSTM
git lfs pull
```

비공개 저장소이므로 본인 GitHub 계정으로 인증해야 합니다. 웹의 ZIP 다운로드는 설정에 따라
LFS 원본 대신 포인터를 포함할 수 있으므로 위 명령을 권장합니다.

복사된 가상환경에는 데스크탑의 절대경로가 남을 수 있습니다. 노트북에서는 복사된
`.venv-ml`을 별도 보관한 뒤 `LAPTOP_CODEX_HANDOFF.md`와 `setup-laptop.cmd`를 이용해
실행 환경을 새로 준비합니다. 설치 도구는 잘못된 기존 환경을 자동 삭제하지 않습니다.
학습된 모델은 다시 학습하지 않고 사용할 수 있습니다. 기존 `main` 브랜치는 유지합니다.

`START_HERE.md`와 인수인계 문서의 ZIP 구성 설명은 별도 경량 전달 ZIP 기준입니다.
이 `master` 브랜치는 그 ZIP에서 제외했던 가상환경과 과거 실험 자료도 포함합니다.
