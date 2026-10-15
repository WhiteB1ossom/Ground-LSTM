"""Build human reports and presentation source data from one verified run."""

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import yaml
from sklearn.metrics import precision_recall_curve


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build(run_dir: Path, build_dir: Path):
    build_dir.mkdir(parents=True, exist_ok=True)
    run = read(run_dir / "run.json")
    bundle_dir = Path(run["stages"]["bundle"]["path"])
    bundle = read(bundle_dir / "bundle.json")
    model_dir = run_dir / "models" / bundle["model_version"]
    report, history = read(model_dir / "report.json"), read(model_dir / "history.json")
    manifest = read(Path(report["dataset_directory"]) / "manifest.json")
    comparison = read(run_dir / "experiment-comparison.json")
    export_dir = Path(run["stages"]["export"]["path"])
    exports = read(export_dir / "export-report.json")
    resources = read(Path(run["stages"]["resources"]["path"]) / "resource-report.json")
    calibrated = Path(run["stages"]["calibrated_replay"]["path"])
    summaries = run["stages"]["calibrated_replay"]["summaries"]
    held, normal = summaries["heldout"]["evaluation"], summaries["long-normal"]["evaluation"]
    policy = read(calibrated / "decision-policy.json")["selected"]
    selected_settings = dict(run["settings"]["replay"])
    selected_settings.update(risk_on_threshold=policy["on"], risk_off_threshold=policy["off"],
                             minimum_consecutive_detections=policy["consecutive"], max_saved_events=1000)
    (run_dir / "replay-selected.yaml").write_text(yaml.safe_dump({"replay": selected_settings}), encoding="utf-8")
    audit = read(Path(run["stages"]["final_audit"]["path"]) / "audit.json")
    tests = ET.parse(run_dir / "tests-final.xml").getroot().find("testsuite")
    assert int(tests.attrib["failures"]) == int(tests.attrib["errors"]) == 0
    test_count = int(tests.attrib["tests"])
    lm, logistic = report["models"]["lstm"]["test"], report["models"]["logistic"]["test"]
    curves = []
    with np.load(model_dir / "test-predictions.npz", allow_pickle=False) as predictions:
        for name in ("logistic", "lstm"):
            precision, recall, _ = precision_recall_curve(predictions["y"], predictions[name])
            curves.append({"name": name, "x": recall.tolist(), "y": precision.tolist()})
    traces, session = [], None
    with (calibrated / "replay/heldout/timeline.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if session is not None and row["session_id"] != session:
                if any(r["ground_truth"] == "risk" for r in traces): break
                traces = []
            session = row["session_id"]
            traces.append(row)
    assert any(r["ground_truth"] == "risk" for r in traces)
    origin = traces[0]["timestamp_ns"]
    times = [(r["timestamp_ns"] - origin) / 1e9 for r in traces]
    scored = [i for i, r in enumerate(traces) if r["prediction"]]
    def spans(predicate):
        result, first = [], None
        for i, row in enumerate(traces):
            if predicate(row) and first is None: first = times[i]
            if first is not None and (not predicate(row) or i == len(traces) - 1):
                result.append([first, times[i] + (.1 if predicate(row) else 0)])
                first = None
        return result
    timeline = {"session": session,
                "sensor": [{"name": "대지전위 a", "x": times, "y": [r["physical_values"]["ground_voltage_a"] for r in traces]},
                           {"name": "자료 기준 2 V", "x": [0, 60], "y": [2, 2]}],
                "score": [{"name": "모델 점수", "x": [times[i] for i in scored], "y": [traces[i]["prediction"]["risk_score"] for i in scored]},
                          {"name": "AI 임계값", "x": [0, 60], "y": [policy["on"], policy["on"]]}],
                "truth_spans": spans(lambda r: r["ground_truth"] == "risk"),
                "alarm_spans": spans(lambda r: r["decision"]["alarm_active"]),
                "unavailable_spans": spans(lambda r: not r["available"])}
    notes = [
        "안녕하세요. 방경식입니다. 이번에는 학습과 링 버퍼의 개별 실행을 연결해, 센서 입력부터 추론, 알림 판단, 이벤트 저장까지 이어지는 PC 프로그램을 구현했습니다. 데이터 수를 늘리고 서로 다른 조건을 시험했으며, 모델 변환과 C++ 전처리 검증도 진행했습니다. 오늘 보여 드리는 성능은 합성 데이터에서의 소프트웨어 검증 결과입니다. 실제 낙뢰 성능이나 보드 탑재를 완료했다는 뜻은 아닙니다.",
        "이 표는 제공 자료의 센서 범위와 기준값입니다. 범위는 입력 품질을 확인하는 범위이고, 위험 판정 기준과는 따로 관리합니다. 누설전류 1밀리암페어는 입력 단위에 맞춰 0.001암페어로 기록했습니다. 대지전위 2와 습도 60퍼센트도 보존했습니다. 다만 초과할 때 위험인지, 미달할 때 위험인지, 같은 값도 포함하는지는 자료만으로 확정하지 않았습니다. 온도 25도도 절대온도인지, 외기온도나 다른 기준 대비 상승량인지 확인이 필요합니다. 코드에서는 초과, 미달, 동일값, 구간 안팎과 같은 비교를 명시하도록 바꿨습니다. 현재 물리 위험 규칙은 비활성 상태입니다. 이 표는 시간별 측정값과 정답이 있는 데이터셋이 아니라 센서 사양입니다.",
        f"학습과 평가에는 60개 합성 시나리오의 36,000행을 사용했습니다. 정상 잡음, 기준 주변 값, 단일 센서 변화, 복합 변화, 위험 전환과 회복을 나눠 만들었습니다. 장애 검증용 6,000행은 학습에 넣지 않았습니다. 별도로 72,000행, 즉 2시간의 정상 연속 입력도 만들었습니다. 전처리 후 학습 {manifest['windows']['train']:,}개, 검증 {manifest['windows']['validation']:,}개, 테스트 {manifest['windows']['test']:,}개로 총 8,100개 입력 창이 생성됐습니다. 같은 획득 세션은 분할에 섞이지 않게 했고, 정규화는 학습 데이터에서만 계산했습니다. 겹치는 창이 있으므로 8,100개를 독립적인 낙뢰 사건 수로 해석하면 안 됩니다.",
        "링 버퍼는 최근 전처리 특징을 고정된 공간에 보관합니다. 이번 선택 모델은 64개 시점을 입력으로 사용하고, 과거 5초분 보관 여유 50개를 더해 버퍼 용량을 114개로 설정했습니다. 표의 번호는 동작 설명용입니다. 115번이 들어오면 가장 오래된 1번 자리를 사용해 2번부터 115번을 유지합니다. 최신 모델 입력도 51번부터 114번에서 52번부터 115번으로 이동합니다. 시간 간격이나 유효성이 맞지 않으면 모델에 이전 입력을 다시 전달하지 않습니다. 원본 관측은 별도 제한된 과거 기록에 보관하고, 경보가 나면 과거 5초와 이후 2초를 이벤트로 저장합니다.",
        f"이 화면은 테스트 입력 중 실제 재생한 한 합성 세션입니다. 위에는 대지전위와 자료의 2볼트 기준선을, 아래에는 모델 점수와 AI 임계값을 같은 시간축에 표시했습니다. 2볼트 선은 위치를 비교하기 위한 자료 기준선이며 자동 위험 판정에 사용하지 않았습니다. 아래 띠는 합성 정답의 위험 구간, 프로그램 경보, 판정 불가 구간입니다. 시작할 때는 64개 시점이 모이지 않아 판정 불가로 표시됩니다. 이후 최근 입력으로 점수를 계산하고, {policy['consecutive']}회 연속 임계값 이상일 때 경보를 시작합니다. 재생 배속을 바꿔도 관측 시각과 경보 시각은 유지합니다. 이 그래프의 시간은 입력 데이터 시간이며 PC 처리 시간이나 센서 전송 지연과는 구분합니다.",
        "모델 크기는 Hidden 16, 32, 64와 다른 seed를 비교했습니다. 추가로 빠른 센서 5종만 사용하는 모델도 시험했습니다. 모델 선택에는 테스트 성능을 사용하지 않고 검증 데이터만 사용했습니다. 이번 합성 조건에서는 Hidden 16, 특징 15개의 후보를 선택했습니다. 15개 특징은 센서값 5개, 결측 표시 5개, 관측 후 경과 시간 5개입니다. 모델 파라미터는 2,065개입니다. 느린 센서의 원본 기록은 계속 보존하며, 실제 데이터에서도 느린 센서가 필요 없다는 결론은 내리지 않았습니다. 긴 온습도 추세를 분석하려면 별도의 장기 입력과 실제 정답 검증이 필요합니다.",
        f"최대 학습 횟수는 50회로 설정했고, 검증 손실에 따라 학습률 감소와 조기 종료를 적용했습니다. 선택 모델은 {report['epochs_completed']}회에서 종료됐고, 최종 저장에는 {report['best_epoch']}회차의 가중치를 사용했습니다. 왼쪽 손실 곡선은 실제 저장된 학습 기록이고, 오른쪽은 별도 테스트의 PR 곡선입니다. 검증 손실이 후반에 증가하는 부분도 그대로 표시했습니다. PR 곡선은 임계값별 precision과 recall의 절충을 보여 줍니다. 면적이 높아도 실제 선택 임계값의 오경보와 미탐지가 없어지는 것은 아니므로 다음 혼동행렬을 함께 봅니다.",
        f"별도 테스트 입력 {lm['samples']:,}개에서 정상 {lm['confusion_matrix'][0][0]:,}개와 위험 {lm['confusion_matrix'][1][1]:,}개를 올바르게 분류했습니다. 정상 입력을 위험으로 예측한 FP는 {lm['false_positives']}개, 위험 입력을 정상으로 예측한 FN은 {lm['false_negatives']}개입니다. Precision은 {lm['precision']:.3f}, Recall은 {lm['recall']:.3f}, F1은 {lm['f1']:.3f}입니다. 같은 데이터의 Logistic은 FN {logistic['false_negatives']}개, FP {logistic['false_positives']}개였습니다. LSTM은 이 시험에서 미탐지가 적은 대신 오경보 입력이 더 많았습니다. 어떤 절충이 적절한지는 실제 운용 요구와 데이터로 결정해야 합니다.",
        f"입력별 FP와 실제 경보 횟수는 다릅니다. 여러 양성 입력이 하나의 경보로 이어질 수 있기 때문입니다. 이번에는 정상 구간에서 경보가 새로 시작하면 오경보 에피소드로 계산하고, 정상 구간에 경보가 유지된 시간도 따로 셌습니다. 혼합 테스트에서 FP는 18개였지만, 정상 구간에서 시작한 새 경보는 {held['false_alarm_episodes']}회였습니다. 위험 후 정상으로 돌아온 뒤 경보가 잠시 유지돼 정상 경보 시간은 {held['normal_alarm_seconds']:.1f}초였습니다. 유효한 정상 시간 대비 약 {held['normal_alarm_fraction']*100:.2f}퍼센트입니다. 합성 위험 구간 8개는 모두 경보와 겹쳤고 감지 지연 중앙값은 {held['median_detection_delay_seconds']:.1f}초였습니다. 별도 2시간 정상 입력에서는 경보가 0회였지만 이 한 시험만으로 실제 오경보율을 보장할 수는 없습니다. 물리 규칙이 확인되면 초과와 미달 조건별로 같은 지표를 다시 분석할 수 있습니다.",
        f"학습 모델을 SavedModel과 float32, float16, INT8 형식으로 변환해 실제 PC 추론을 실행했습니다. float32는 {exports['formats']['float32']['bytes']:,}바이트, float16은 {exports['formats']['float16']['bytes']:,}바이트였습니다. 두 형식의 테스트 판정 변화는 0개였습니다. INT8은 반복 계산을 펼친 그래프 때문에 {exports['formats']['int8']['bytes']:,}바이트로 커졌고, 판정도 2개 달라져 FP가 18개에서 20개가 됐습니다. 따라서 INT8이 항상 작거나 좋은 것은 아닙니다. C++ 전처리와 링 버퍼는 기준 입력 140개로 Python 결과와 일치함을 확인했습니다. 전체 자동 테스트는 {test_count}개를 통과했습니다. 확인한 링, 입력, 작업 공간의 합은 12,282바이트지만 이것은 전체 MCU RAM이 아닙니다. 실제 보드의 연산자 지원, tensor arena, firmware와 처리 기한은 아직 검증하지 않았습니다.",
        "현재 PC에서는 수신, 전처리, 링 버퍼, 모델 추론, 알림 판단, 이벤트 저장, 재생과 평가가 연결됩니다. 이벤트 저장 실패나 입력 장애를 정상 판정으로 바꾸지 않고 사유를 기록합니다. 다음은 세 가지입니다. 먼저 회사와 센서 기준의 방향, 단위, 온도 기준과 허용 오경보 및 지연을 확정해야 합니다. 다음으로 실제 측정값과 독립적인 정답을 확보해 재학습하고 조건별 테스트를 늘려야 합니다. 마지막으로 실제 통신 규격에 맞춘 어댑터와 목표 MCU를 연결해 메모리, 연산자와 최악 처리 시간을 측정해야 합니다. 현재 예측 대상은 입력 종료 시점의 상태이며, 미래 낙뢰 예측을 검증한 모델은 아닙니다."
    ]
    sources = [
        "artifacts/integrated-20261012/run.json, docs/integrated-development-plan-20261012.md",
        "configs/sensor_standard_reference.yaml; 원본 교육계획서 PDF 6페이지. 입력전압 범위 셀의 단위 미기재; 모든 원문 행 5 bytes. RMS/peak, 초과/미달, 온도 기준 미확정.",
        "scenarios.json, dataset-fast-only/manifest.json, train.npz / validation.npz / test.npz. 정답은 물리 규칙과 별도로 만든 합성 잠재 상태.",
        "src/realtime/ring_buffer.py, sequence_builder.py, recorder.py; calibrated replay summary. 1~115는 설명용 번호.",
        f"{calibrated}/replay/heldout/timeline.jsonl; 합성 세션 {session}. 100ms 정렬, stride 4, on=off={policy['on']}, 연속 {policy['consecutive']}회. 원본 관측 주기는 센서별 유지.",
        "experiment-comparison.json, models/lstm16-fast-only/report.json. Hidden/seed/특징 실험 5개, validation 전용 선택.",
        "models/lstm16-fast-only/history.json, test-predictions.npz, report.json; sklearn precision_recall_curve. https://keras.io/api/layers/recurrent_layers/lstm/",
        "models/lstm16-fast-only/report.json models.lstm.test / models.logistic.test. 새로운 합성 fixture이며 이전 FP46 실험과 직접 증감 비교 불가.",
        "calibrated-3 replay summaries; src/evaluation/stream_metrics.py. False alarm=available labeled NORMAL에서 ENTER. 정상 유지 시간과 unmatched episode 별도. 위험 구간 매칭=경보 유효 구간의 겹침.",
        "export-verified-4/export-report.json, resources-verified-3/resource-report.json, final-audit/audit.json, tests-final.xml. https://developers.google.com/edge/litert/microcontrollers/overview ; https://github.com/tensorflow/tflite-micro/blob/main/tensorflow/lite/micro/docs/memory_management.md",
        "docs/integrated-development-plan-20261012.md; configs/target_mcu.yaml. 실제 기준, 실측 정답, 패킷 규격, MCU/자원 예산 외부 정보 미제공."
    ]
    payload = {"run_id": run["run_id"], "test_count": test_count, "notes": notes, "sources": sources,
               "timeline": timeline, "loss": [{"name": "train", "x": list(range(1, len(history['loss']) + 1)), "y": history["loss"]},
                                               {"name": "validation", "x": list(range(1, len(history['val_loss']) + 1)), "y": history["val_loss"]}],
               "pr": curves, "report": report, "comparison": comparison, "exports": exports,
               "resources": resources, "heldout": held, "normal": normal, "policy": policy}
    (build_dir / "content.json").write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    script = "# 실시간 통합 개발 발표 대본\n\n실험: integrated-20261012. PPT 11장과 같은 순서. 약 7~9분이며 숫자를 읽는 속도에 따라 조절합니다.\n\n"
    titles = ["실시간 통합 개발", "센서 범위와 판정 기준", "확대 데이터 구성", "링 버퍼와 이벤트 기록", "실제 재생 타임라인", "모델 후보 비교", "학습 곡선과 PR 곡선", "테스트 분류 결과", "오경보와 시간 평가", "모델 변환과 임베디드 준비", "남은 확인과 개발"]
    for i, (title, note) in enumerate(zip(titles, notes), 1): script += f"## {i}. {title}\n\n{note}\n\n"
    output = Path("output/presentations")
    output.mkdir(parents=True, exist_ok=True)
    (output / "그라운드_실시간_통합개발_발표대본_방경식.md").write_text(script, encoding="utf-8")
    rows = "\n".join(f"| {c['name']} | {c['resources']['parameters']:,} | {c['validation']['recall']:.4f} | {c['validation']['f1']:.4f} |" for c in comparison["candidates"])
    doc = f"""# 실시간 통합 개발·검증 결과

작성일 2026-10-12 · 실험 `{run['run_id']}` · 상태 `{run['status']}`

PC의 입력→전처리→링 버퍼→시퀀스→추론→판단→이벤트 기록→평가를 연결하고 실제 실행했다. 아래 성능은 합성 소프트웨어 시험 결과이며 실제 낙뢰 성능과 MCU 탑재 완료를 의미하지 않는다. 이전 모델·데이터·PPT는 보존했다.

## 요구별 완료와 증거

| 항목 | 현재 상태 | 증거 |
|---|---|---|
| 센서 범위·기준값 | 원문 숫자 보존; 방향·온도 기준 미확정 | `configs/sensor_standard_reference.yaml` |
| 명시 규칙 | gt/ge/lt/le/eq/inside/outside, 차이, 단위, AND/OR, unknown 구현 | `src/models/rules.py`, 경계 테스트 |
| 입력·전처리 | CSV/Parquet 스트림, 같은 시각 센서 병합, 역순·중복 거부, causal 정렬/age/mask | `src/realtime/reader.py`, `stream.py` |
| 연속 입력 | 정답/event_id에 의한 초기화 제거, 획득 세션 경계, 단일 장치 소유 | session 정책 테스트 |
| 학습·선택 | 모델 5개 실제 학습, validation 전용 선택, train-only scaler | `experiment-comparison.json` |
| 추론 계약 | shape·feature·설정·파일 해시 검사, READY 입력만 사용, stateless | `final-audit/audit.json` |
| 알림 판단 | on/off 경계, 연속 확인, NORMAL/RISK/UNAVAILABLE; 장애 중 기존 경보 유지 | `src/realtime/decision.py` |
| 이벤트 기록 | 원본·특징·입력 사유·점수·버전; 전 5초/후 2초, 제한 큐/별도 writer/원자 저장 | calibrated replay events 및 recorder 테스트 |
| 저장 한도 | history 51행, 활성 이벤트 4개, 큐 64개, 최대 파일 1,000개; 초과/실패 명시 | `recorder.py` |
| 재생·평가 | 1x/2x/10x/max 가상 시각 검증, 정상/위험/오류/2시간 정상 | replay summaries, 속도 테스트 |
| 변환 | SavedModel 재로딩, float32/float16/INT8 실행·출력 비교 | export report |
| C++ 준비 | C 배열·정규화 상수, portable 전처리·링·판단; MSVC host 140개 기준 입력 일치 | resource report, host-build.log |
| 실제 장치 | 통신 adapter, TFLM kernel/arena/firmware/MCU deadline 미검증 | 목표 보드·프로토콜 정보 필요 |

확인되지 않은 물리 규칙은 `rules: []`로 비활성이다. 기준 미달/동일/초과는 테스트할 수 있지만 어느 방향이 실제 위험인지 승인한 상태는 아니다. 느린 센서의 장기 추세, 실제 미래 예측, 새 multiclass 의미는 해당 데이터·정답이 없어 활성화하지 않았다. 코드의 비교 연산자는 소프트웨어 기능이며 실제 안전 기준이 아니다.

## 데이터와 모델

- 학습·평가 원본 36,000행 / 60개 획득 시나리오: 36/12/12 세션 분리.
- 오류 원본 6,000행 / 10개: label 없음, 성능 학습에 사용하지 않음.
- 별도 정상 연속 원본 72,000행 / 2시간: 평가 전용, 위험 정답 없음.
- 입력 창: Train 4,860 / Validation 1,620 / Test 1,620 = 8,100.
- 선택 입력: 빠른 센서 5종 × 현재값/결측/age = 15개 특징; shape `1×64×15`, nominal 6.4초, 끝점 간격 6.3초.
- 정렬 100ms, stride 4: 입력 관측을 복제하지 않고 최근 관측을 causal 유지하며 약 400ms마다 창 추론.
- Hidden 16 / 단방향 1층 / 파라미터 2,065 / batch 64 / 최대 50 epochs.
- 실제 {report['epochs_completed']} epochs에서 조기 종료; 최적 검증 손실 가중치는 {report['best_epoch']}회차.
- Label horizon 0: 현재 상태 감지. 점수는 보정된 실제 낙뢰 확률이 아님.

| 후보 | 파라미터 | Validation recall | Validation F1 |
|---|---:|---:|---:|
{rows}

선택은 validation만 사용했다. 빠른 센서 후보가 이번 합성 조건에서 선택됐으며 온습도·제한소자 온도가 실제 현장에서 불필요하다는 뜻은 아니다. 8,100개 창은 일부 겹치며 독립적인 8,100개 사건이 아니다. 센서 표의 범위·주기·단위는 참조했지만 정답은 별도 합성 잠재 상태에서 생성했다. 물리 현상을 재현하거나 독립적인 실측 label을 대체하지 않는다.

## 최종 분류와 경보 평가

| Test 모델 | Precision | Recall | F1 | FN | FP |
|---|---:|---:|---:|---:|---:|
| Logistic | {logistic['precision']:.4f} | {logistic['recall']:.4f} | {logistic['f1']:.4f} | {logistic['false_negatives']} | {logistic['false_positives']} |
| 선택 LSTM | {lm['precision']:.4f} | {lm['recall']:.4f} | {lm['f1']:.4f} | {lm['false_negatives']} | {lm['false_positives']} |

LSTM 혼동행렬: 행=실제 정상/위험, 열=예측 정상/위험, `[[1437,18],[1,164]]`. 정상 분모 1,455개 중 FP18 (1.237%); 위험 분모 165개 중 FN1 (0.606%). LSTM은 Logistic보다 FN이 적고 FP가 많았다. 이전 FP46 실험과 데이터/입력/분할이 달라 개선 비율을 직접 계산하지 않는다.

AI on/off={policy['on']:.8f}, 연속 {policy['consecutive']}회는 validation에서 정했다. 같은 on/off가 선택되어 이 run에는 추가 히스테리시스 간격이 없으며 기능 자체는 지원한다. 검증 recall 목표는 소프트웨어 후보 필터일 뿐 회사가 승인한 안전 요구가 아니다.

- **입력 FP**: 정답 정상 창에서 점수≥AI 임계값. 테스트 18개.
- **오경보 에피소드**: 유효한 정답 정상 시각에 ENTER가 발생한 횟수. 혼합 시험 {held['false_alarm_episodes']}회.
- **정상 경보 시간**: 위험에서 시작한 경보가 정상까지 지속된 시간도 포함. {held['normal_alarm_seconds']:.1f}초 / 유효 정상 {held['normal_valid_seconds']:.1f}초 = {held['normal_alarm_fraction']*100:.3f}%.
- **사건 감지**: 유효 경보가 위험 구간과 겹치면 감지. 합성 위험 {held['risk_intervals']}구간 중 {held['detected_risk_intervals']}구간 감지; 지연 중앙값 {held['median_detection_delay_seconds']:.1f}초 (입력 시각 기준, 미래 예측 선행 시간 아님).
- **Coverage**: 혼합 재생 {held['coverage']*100:.1f}%. 12개 획득 세션 각각 시작 6.3초는 준비 시간; 위험 구간의 불완전 coverage는 0개.
- **2시간 정상**: 72,000행, 17,985개 추론 창, 새 경보 0회, 정상 경보 시간 0초, coverage {normal['coverage']*100:.4f}%. 양성 정답이 없어 recall/F1의 의미 있는 평가가 불가능하며 실제 오경보율 보장이 아님.
- **오류 입력**: 6,000행 원본, 실제 정렬 {summaries['faults']['aligned_rows']:,}행, coverage {summaries['faults']['evaluation']['coverage']*100:.2f}%. label 없음; FP/FN 계산하지 않음. 구 버전 합성 timestamp의 미세 jitter로 정렬 행 차이가 있었고 이후 생성기는 정수 ns 시간으로 수정; 기존 원본은 유지.

물리 규칙 충족/미충족 × 정답 × 예측의 8칸 평가 집계도 구현했다. 현재 물리 규칙 비활성으로 모든 점수 창의 규칙 조건은 UNKNOWN이다. UNKNOWN을 기준 미달이나 정상으로 바꾸지 않는다. 초과/미달, 동일값, 순간/지속 이탈, 온도 차이와 복합 조건은 확인된 규칙을 입력한 다음 이 표로 해석해야 한다.

## 변환·자원·검증

| 형식 | 파일 bytes | Test 판정 변화 | Test FP/FN | 출력 최대 오차 |
|---|---:|---:|---|---:|
"""
    for kind, item in exports["formats"].items():
        doc += f"| {kind} | {item['bytes']:,} | {item['classification_changes']} | {item['test']['false_positives']}/{item['test']['false_negatives']} | {item['max_output_error']:.8f} |\n"
    doc += f"""
Float 모델은 반복 그래프를 유지했고 INT8은 동일 가중치의 반복 계산을 펼쳤다. INT8은 연산 그래프가 커져 Flash 파일이 더 크고 FP도 2개 늘어 이번 C 배열 후보는 float32다. 실제 MCU 연산자 지원과 자원 예산에 따라 다른 구조가 필요할 수 있다. 중첩 WHILE의 연산자까지 `final-audit/audit.json`에 기록했다. 변환 실패 이력/로그도 보존했다.

Ring 배열 payload 7,866B + 입력 3,840B + 시퀀스 workspace 576B = 알려진 RAM 하한 12,282B. Python 객체·원본 기록·writer·stack·tensor arena·firmware는 포함하지 않았다. Flash/RAM/CPU/board가 미확정이므로 탑재 가능성은 **UNKNOWN**이다. Portable host 빌드는 TFLM adapter 또는 MCU firmware 빌드가 아니다. PC latency를 MCU latency로 사용하지 않는다.

전체 테스트 **{test_count}개 통과**. Keras/NumPy 연동의 DeprecationWarning 45건은 별도 보존했다. 파일 hash·입력 계약 변조 거부, 같은 입력 반복과 A/B/A 독립성, READY 실패 입력 재사용 금지, 경계/회복/장애, pre/post/EOF/디스크 실패/큐 초과/파일 한도, 세션·event ID 충돌과 배속을 검사했다. Keras와 float32 LiteRT 연속 재생 {audit['keras_litert_replay_rows_identical']:,}행의 상태·판단이 동일하고 점수 최대 오차는 {audit['max_replay_score_error']:.9g}였다. C++ 기준 입력 140개 일치도 host에서 실제 실행했다.

## 남은 외부 확인과 보완

1. 센서 기준의 초과/미달·동일값·온도 기준·RMS/peak·입력전압 단위와 사용전압, 실제 허용 경보/미탐지/지연 확정.
2. 실측 원본과 독립 label/onset, 여러 장치·환경의 독립 세션 수집, 실제 조건별 Test 확대 및 재학습.
3. UART/CAN 등의 실제 패킷, 상태·timestamp/clock 동기화 규격과 별도 surge adapter 연결.
4. 목표 MCU/toolchain과 TFLM kernel·arena·firmware·전체 RAM/Flash·최악 처리시간·clock wrap 측정.
5. 필요한 경우 장기 온습도 특징, 확정 multiclass 또는 미래 horizon 모델을 별도 검증. 현재 기능으로 완료를 주장하지 않음.

작동 방법은 [통합 실행 가이드](integration-usage.md), 설계 기준은 [통합 계획](integrated-development-plan-20261012.md) 참조. 결과 기준은 `artifacts/integrated-20261012/run.json`의 stage 경로이며 과거 실패/다른 모델의 export 경로와 혼용하지 않는다.
"""
    Path("docs/integration-results-20261012.md").write_text(doc, encoding="utf-8")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.run, args.build_dir)
    print(json.dumps({"test_count": result["test_count"], "slide_count": len(result["notes"])}))
