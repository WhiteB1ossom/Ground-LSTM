"""Check the final form, source preservation and report claims before publication."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path("artifacts/report-new-20261016/tools").resolve()))
from hwpx import HwpxDocument


ROOT = Path.cwd()
WORK = ROOT / "artifacts/report-new-20261016"
source = json.loads((WORK / "reference-4.json").read_text(encoding="utf-8"))
final = json.loads((WORK / "report-5-roundtrip.json").read_text(encoding="utf-8"))
render = json.loads((WORK / "render-report.json").read_text(encoding="utf-8"))
if render["total_pages"] != 3 or not render["complete"]:
    raise ValueError("Expected cover plus two complete body pages")
if any(i["stage"] == "layout" for i in render["issues"]):
    raise ValueError("Unresolved layout issue")
def words(node):
    if isinstance(node, dict):
        if "Text" in node:
            yield node["Text"]
        else:
            for value in node.values():
                yield from words(value)
    elif isinstance(node, list):
        for value in node:
            yield from words(value)
text = "".join(words(final["sections"]))
for expected in ("( 5 )회차", "그림 1", "그림 2", "153,000", "30,600", "2,958", "0.9993", "1.0000", "345",
                 "실제 장비 고장·낙뢰 정확도로 해석하지 않는다", "오탐지(FP)", "미탐지(FN)", "21개 경계 상황",
                 "2.000mA는 동일·충족", "시간당 시작 횟수", "정답 미확인", "검토 의견", "서지 없는 발열"):
    if expected not in text:
        raise ValueError(f"Missing report content: {expected}")
if "그림삽입" in text or "2026 년 10 월 7 일" in text or "13:00" in text:
    raise ValueError("Placeholder or obsolete attendance date remains")
original_paras, final_paras = source["sections"][0]["paragraphs"], final["sections"][0]["paragraphs"]
for source_index, final_index in ((3, 3), (9, 9), (18, 18), (23, 23), (24, 24), (23, 25), (24, 26)):
    a = original_paras[source_index]["controls"][0]["Table"]
    b = final_paras[final_index]["controls"][0]["Table"]
    for key in ("rows", "cols", "border_fill", "inner_margins"):
        if a[key] != b[key]:
            raise ValueError(f"Form changed: table {final_index} {key}")
    for ca, cb in zip(a["cells"], b["cells"], strict=True):
        for key in ("row", "col", "row_span", "col_span", "width", "height", "margins", "border_fill"):
            if ca[key] != cb[key]:
                raise ValueError(f"Form geometry changed: table {final_index} {key}")
old_page = original_paras[0]["controls"][0]["SectionDef"]["page"]
new_page = final_paras[0]["controls"][0]["SectionDef"]["page"]
if old_page != new_page:
    raise ValueError("Page settings changed")
if len(final["bin_streams"]) != 2:
    raise ValueError("Expected two embedded visuals")
for index in (24, 26):
    cells = final_paras[index]["controls"][0]["Table"]["cells"]
    if "2026 년     월     일 (    요일)" not in "".join(words(cells[1]["paragraphs"])):
        raise ValueError("An attendance date was filled")
native_check = HwpxDocument.open(WORK / "report-5.hwp")
conversion = native_check.conversion_report
if conversion.unconverted or conversion.dropped:
    raise ValueError(f"Independent parser lost report content: {conversion}")
originals = json.loads((WORK / "original-hashes.json").read_text(encoding="utf-8"))
for name, digest in originals.items():
    if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
        raise ValueError("An original report was changed")
target = ROOT.parent / "그라운드 보고서 방경식 5회차.hwp"
prior = json.loads((WORK / "prior-publication.json").read_text(encoding="utf-8"))
if hashlib.sha256(target.read_bytes()).hexdigest() != prior["sha256"]:
    raise ValueError("Published report changed since revision began")
if hashlib.sha256(Path(prior["backup"]).read_bytes()).hexdigest() != prior["sha256"]:
    raise ValueError("Previous report backup is invalid")
with target.open("wb") as handle:
    handle.write((WORK / "report-5.hwp").read_bytes())
verification = {"status": "PASS", "output": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "pages": 3, "cover_pages": 1, "body_pages": 2, "embedded_visuals": 2,
                "form_tables_preserved": 5, "matching_continuation_tables": 2, "originals_unchanged": len(originals),
                "round": 5, "attendance_date_and_time": "BLANK", "independent_hwp_parser": "PASS_NO_DROPPED_OR_UNCONVERTED_ITEMS",
                "visual_qa": "COVER_AND_TWO_BODY_PAGES_INSPECTED", "native_hancom_open": "UNAVAILABLE_COM_SERVER_EXECUTION_FAILURE_0x80080005",
                "render_font_substitutions": render["font_coverage"]["substituted"], "physical_measurement_performance_claimed": False,
                "previous_version_backup": prior["backup"], "feedback_and_false_alarm_definitions_included": True}
(WORK / "verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(verification, ensure_ascii=False, indent=2))
