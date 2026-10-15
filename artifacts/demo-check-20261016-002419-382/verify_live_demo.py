"""Exercise the running demo via HTTP, retaining actual-model evidence."""
import json
from pathlib import Path
import re
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:8765"


def state():
    with urllib.request.urlopen(BASE + "/api/state", timeout=5) as response:
        result = json.load(response)
    if result["status"] == "ERROR":
        raise AssertionError(result["error"])
    return result


def wait_for(predicate, limit=60):
    end = time.monotonic() + limit
    while time.monotonic() < end:
        s = state()
        if predicate(s):
            return s
        time.sleep(.1)
    raise AssertionError("Timed out")


with urllib.request.urlopen(BASE) as response:
    token = re.search(r"const token='([^']+)'", response.read().decode("utf-8")).group(1)


def command(**message):
    request = urllib.request.Request(BASE + "/api/control", data=json.dumps(message).encode(),
                                     headers={"X-Demo-Token": token, "Content-Type": "application/json"})
    with urllib.request.urlopen(request) as response:
        assert response.status == 202


ready = wait_for(lambda s: s["status"] == "READY")
assert len(ready["cases"]) == 17
command(action="speed", value=20)
report = {"actual_lstm": True, "synthetic_demo": True, "cases": {}}
for kind in ("normal", "surge_only", "heating_without_surge", "both", "counter_reset"):
    selected = next(c for c in ready["cases"] if c["scenario"] == kind)
    command(action="start", case=selected["id"])
    warm = wait_for(lambda s: s["demo"] and s["demo"]["session_id"] == selected["id"] and s["demo"]["progress"] >= 10)
    assert warm["effective_speed"] == 1
    assert warm["demo"]["ring"]["size"] < 64
    if kind == "normal":
        command(action="pause")
        paused = wait_for(lambda s: s["status"] == "PAUSED")
        time.sleep(.35)
        assert state()["demo"]["progress"] == paused["demo"]["progress"]
        command(action="resume")
        report["pause_resume"] = "PASS"
    finished = wait_for(lambda s: s["status"] == "FINISHED" and s["demo"]["session_id"] == selected["id"])
    demo = finished["demo"]
    assert demo["progress"] == 1800 and demo["ring"]["size"] == 114 and demo["ring"]["overwritten"] == 1686
    assert demo["processing_failures"] == 0
    assert all(t["inferences"] == 174 for t in demo["tasks"].values())
    output = Path(demo["output"])
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "COMPLETE" and summary["timeline"]["error_count"] == 0
    alarms = {t: 0 for t in ("degradation", "surge")}
    resets = 0
    states = set()
    for name in summary["timeline"]["files"]:
        with (output / name).open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                states.add(row["state"])
                resets += row["equipment"]["counter"]["reset"]
                for task in alarms:
                    alarms[task] += row["tasks"][task]["decision"]["alarm_active"]
    if kind in {"normal", "counter_reset"}:
        assert not any(alarms.values())
    elif kind == "surge_only":
        assert alarms["surge"] > 0 and alarms["degradation"] == 0
    elif kind == "heating_without_surge":
        assert alarms["degradation"] > 0 and alarms["surge"] == 0
    else:
        assert "EQUIPMENT_REVIEW_AND_SURGE" in states
    assert resets == (1 if kind == "counter_reset" else 0)
    report["cases"][kind] = {"observations": demo["progress"], "inferences": summary["inferences"],
                             "alarm_rows": alarms, "states": sorted(states), "counter_resets": resets, "output": str(output)}
    (ROOT / "live-verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(kind + ": PASS", flush=True)
report["status"] = "PASS"
(ROOT / "live-verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
# Leave a fresh paused acquisition for the presenter.
command(action="start", case=next(c for c in ready["cases"] if c["scenario"] == "both")["id"])
wait_for(lambda s: s["status"] == "RUNNING" and s["demo"]["scenario"] == "both")
command(action="pause")
wait_for(lambda s: s["status"] == "PAUSED")
print("All five actual-model scenarios and pause/resume: PASS", flush=True)
