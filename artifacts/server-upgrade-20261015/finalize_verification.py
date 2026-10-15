"""Consolidate actual tests, saved models, replay evidence and original hashes."""

import compileall
from copy import deepcopy
import difflib
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


root = Path.cwd()
output = Path(__file__).parent.resolve()
run = root / "artifacts/server-equipment-20261015"
runtime = json.loads((output / "runtime-verification.json").read_text(encoding="utf-8"))
assert runtime["status"] == "SUCCESS"
state = json.loads((run / "run.json").read_text(encoding="utf-8"))
assert state["status"] == "SERVER_SOFTWARE_COMPLETE_PHYSICAL_VALIDATION_PENDING"
assert compileall.compile_dir(root / "src", quiet=1)
assert compileall.compile_dir(root / "scripts", quiet=1)
tests = ET.parse(output / "tests-final.xml").getroot().findall("testsuite")
counts = {key: sum(int(t.attrib[key]) for t in tests) for key in ("tests", "errors", "failures", "skipped")}
assert counts == {"tests": 319, "errors": 0, "failures": 0, "skipped": 0}, counts
equipment_cases = [case for suite in tests for case in suite.findall("testcase") if case.attrib.get("classname", "").split(".")[-1] == "test_equipment_server"]
assert len(equipment_cases) == 34
focused = ET.Element("testsuites")
suite = ET.SubElement(focused, "testsuite", name="equipment subset of tests-final.xml", tests="34", errors="0", failures="0", skipped="0",
                      time=str(sum(float(case.attrib["time"]) for case in equipment_cases)))
for case in equipment_cases: suite.append(deepcopy(case))
ET.ElementTree(focused).write(output / "tests-equipment.xml", encoding="utf-8", xml_declaration=True)
protected = json.loads((output / "protected-hashes.json").read_text(encoding="utf-8"))
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert all(digest(root / name) == value for name, value in protected.items())
baseline = json.loads((output / "baseline/hashes.json").read_text(encoding="utf-8"))
diff = []
for name, value in baseline.items():
    before = output / "baseline" / name
    assert digest(before) == value
    diff.extend(difflib.unified_diff(before.read_text(encoding="utf-8").splitlines(True),
                                    (root / name).read_text(encoding="utf-8").splitlines(True), fromfile="baseline/"+name, tofile=name))
(output / "changed-sources.diff").write_text("".join(diff), encoding="utf-8")
new = ["src/features/equipment.py", "src/realtime/equipment_server.py", "scripts/prepare_equipment_data.py",
       "scripts/run_equipment_server.py", "tests/test_equipment_server.py", "configs/equipment_server.yaml",
       "configs/sensors_equipment_server.yaml", "configs/preprocessing_equipment_server.yaml", "docs/equipment-server-20261015.md"]
result = {"schema_version": 1, "status": "SUCCESS", "tests": counts, "new_regression_cases": 34,
          "existing_dependency_warnings": 45, "compileall": "SUCCESS", "protected_files": len(protected), "protected_changed": [],
          "runtime": runtime, "server_run_status": state["status"],
          "source_sha256": {name: digest(root/name) for name in [*baseline, *new]},
          "physical_validation": False, "hardware_actuation_performed": False,
          "criteria_scope": "User-provided review values with explicit engineering defaults, not certified company thresholds"}

lines = ["", "## 검증 결과", "", "전체 테스트 **319개**, 새 회귀 시험 **34개**가 통과했다. 기존 Keras/NumPy DeprecationWarning 45개는 남는다.", "",
         "| 작업 | 선택 LSTM | 완료 epoch / 최적 epoch | Test F1 | Test 재현율 | Test FP / FN |",
         "|---|---|---|---|---|---|"]
for task, entry in runtime["selection"].items():
    metric = entry["test"]
    lines.append(f"| {task} | {entry['selected']} | {entry['epochs_completed']} / {entry['best_epoch']} | {metric['f1']:.4f} | {metric['recall']:.4f} | {metric['false_positives']} / {metric['false_negatives']} |")
lines += ["", "표는 작업별 Test 입력 창 2,958개에 대한 분류 지표이며, 실제 낙뢰 사건 수나 장비 고장 확률이 아니다.", "",
          "- 각 작업의 실제 Keras 모델로 Test 30,600행을 재생했다. 10개 센서와 39개 특징을 유지했다.",
          "- 작업별 2,958개 Test 창에서 저장된 학습 입력과 현재 실시간 경로의 입력 텐서가 정확히 일치했고, 저장된 Test 점수와의 최대 차이는 다음과 같다: " + json.dumps(runtime["maximum_score_error"]),
          "- 두 작업을 함께 출력하는 CLI도 9,000행에서 정상 종료했고, 두 이벤트 recorder의 저장 완료를 확인했다.",
          "- 기준 7개의 미달·동일·초과 21개 경계 상황을 실모델 경로에 통과시켜 점검 조건을 확인했다. 이 상황의 물리 고장 정답은 UNLABELED로 유지했다.",
          "- 두 모델을 다른 폴더로 복사해 상대경로 연결과 동일 입력 출력을 확인했다. 실제 노트북의 새 설치 환경을 시험한 것은 아니다.",
          "- 실제 TensorFlow 오류를 주입해 전체 판정 불가, 기존 서지 경보 유지, 이후 복구를 확인했다.",
          "- 관측 카운터 증가를 직접 사용하는 기준선과 AI 점수를 따로 기록했다. 카운터 증가 자체를 실제 낙뢰의 독립 정답으로 주장하지 않는다.",
          "- 이전 모델·선택 설정·발표자료 등 98개 원본 파일의 SHA256이 모두 유지됐다.",
          "- 증거는 `artifacts/server-upgrade-20261015/tests-final.xml`, `tests-equipment.xml`, `runtime-verification.json`, `verification.json`, `training.log`에 있다.",
          "", "합성 데이터는 모델 구조와 소프트웨어 동작을 검증하는 용도다. 실측 정답, 실제 서버 환경, 장비별 전압 기준과 전압 응답은 별도 확인해야 한다."]
doc = root / "docs/equipment-server-20261015.md"
content = doc.read_text(encoding="utf-8").split("\n## 검증 결과", 1)[0]
doc.write_text(content.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
# The generated report is part of this final snapshot.
result["source_sha256"]["docs/equipment-server-20261015.md"] = digest(doc)
(output / "verification.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
print(json.dumps({"status": "SUCCESS", "tests": counts, "protected_files": len(protected),
                  "server_run_status": state["status"], "selected": {t: v["selected"] for t, v in runtime["selection"].items()}}))
