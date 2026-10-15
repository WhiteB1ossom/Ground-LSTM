"""Demo lifecycle uses the production causal pipeline; HTTP never owns the model."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import threading

import numpy as np
import pytest

from src.features.transform import FeatureTransform
from src.preprocessing.scaling import FrozenScaler
from src.realtime.demo import DemoController, DemoSession, load_cases, make_handler
from src.realtime.equipment_server import EquipmentServer, TASKS
from src.realtime.stream import RealtimePipeline
from src.utils.config import load_config, read_yaml


@pytest.fixture
def server():
    config = load_config("configs/preprocessing_equipment_server.yaml")
    order = FeatureTransform(config.sensors, config.settings["pipeline"]).order
    scaler = FrozenScaler(order, "standard").fit(np.stack([np.zeros(39), np.ones(39)]), split="train")
    class Engine:
        shape, threshold = (1, 64, 39), .5
        manifest = {"configuration": config.settings, "sensors": [vars(s) for s in config.sensors], "model_version": "test-engine"}
        def predict(self, tensor):
            return {"risk_score": .9, "inference_ms": .01}
    engine = Engine()
    engine.scaler = scaler
    settings = read_yaml(Path("configs/equipment_server.yaml"))["replay"]
    result = EquipmentServer.__new__(EquipmentServer)
    result.pipelines = {t: RealtimePipeline(engine, deepcopy(settings)) for t in TASKS}
    return result


def case(count=125):
    rows = []
    for i in range(count):
        rows.append({"timestamp": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=i / 10)).isoformat(),
                     "ground_voltage_a": .5, "ground_voltage_b": .5, "leakage_current": .0015,
                     "limiter_temp_a": 30., "limiter_temp_b": 31., "limiter_temp_c": 32.,
                     "humidity": 50., "ambient_temp": 25., "input_voltage": 220., "lightning_sensor": 1000.,
                     "device_id": "d", "session_id": "s", "scenario": "normal", "acquisition_kind": "synthetic",
                     "is_synthetic": True, "degradation_truth": "risk" if i % 2 else "normal", "surge_truth": "normal"})
    return {"id": "s", "scenario": "normal", "rows": rows, "times": [i / 10 for i in range(count)]}


def test_ring_inference_and_labels_do_not_reset_acquisition(server, tmp_path):
    source = case()
    original = deepcopy(source)
    session = DemoSession(server, source, tmp_path / "replay")
    for _ in range(63):
        session.step()
    assert session.warming and not session.predictions
    while not session.done:
        session.step()
    snapshot = session.snapshot()
    assert snapshot["ring"] == {"size": 114, "capacity": 114, "window": 64, "features": 39, "stride": 10, "overwritten": 11}
    assert snapshot["tasks"]["degradation"]["inferences"] == 7
    assert snapshot["tasks"]["degradation"]["alarm_active"]
    snapshot["tasks"]["degradation"]["prediction"]["risk_score"] = 0
    assert session.predictions["degradation"]["risk_score"] == .9
    assert source == original
    session.close("COMPLETE")
    summary = json.loads((session.output / "summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "COMPLETE" and summary["timeline"]["written_records"] == 125
    first = json.loads((session.output / "timeline.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert first["timestamp"] == source["rows"][0]["timestamp"]
    session.close("INTERRUPTED")
    with pytest.raises(RuntimeError):
        session.step()


def test_explicit_new_case_reuses_models_but_starts_empty_buffer(server, tmp_path):
    first = DemoSession(server, case(), tmp_path / "first")
    for _ in range(70):
        first.step()
    engines = {t: p.engine for t, p in server.pipelines.items()}
    first.close("INTERRUPTED")
    second = DemoSession(server, case(), tmp_path / "second")
    assert second.snapshot()["ring"]["size"] == 0
    assert all(p.engine is engines[t] and not p.decision.active for t, p in server.pipelines.items())
    second.close("INTERRUPTED")


def test_inference_failure_remains_visible_and_save_is_degraded(server, tmp_path):
    for p in server.pipelines.values():
        def fail(_tensor):
            raise RuntimeError("injected failure")
        p.engine.predict = fail
    session = DemoSession(server, case(75), tmp_path / "failed")
    while not session.done:
        session.step()
    assert session.snapshot()["state"] == "UNAVAILABLE" and session.failures > 0
    assert any("injected failure" in e["text"] for e in session.events)
    session.close("COMPLETE")
    assert json.loads((session.output / "summary.json").read_text())["status"] == "DEGRADED"


def test_catalog_preserves_whole_synthetic_acquisition_and_timestamps(tmp_path):
    import csv
    path = tmp_path / "observations.csv"
    rows = case(3)["rows"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = load_cases(path, ["ambient_temp"])
    assert result["s"]["times"] == [0., .1, .2] and len(result["s"]["rows"]) == 3
    path.write_text(path.read_text().replace("True", "False"))
    with pytest.raises(ValueError, match="synthetic"):
        load_cases(path, ["ambient_temp"])


@pytest.mark.parametrize("message", [{"action": "speed", "value": True}, {"action": "speed", "value": 0},
                                       {"action": "start", "case": "../secret"}, {"action": "delete"}, []])
def test_control_rejects_invalid_input(message, tmp_path):
    controller = DemoController(tmp_path, tmp_path / "raw/data.csv", tmp_path / "output")
    controller.publish(status="READY", cases=[{"id": "s"}])
    with pytest.raises(ValueError):
        controller.control(message)


def test_worker_startup_error_is_exposed(monkeypatch, tmp_path):
    def fail(_run):
        raise ValueError("broken bundle")
    monkeypatch.setattr("src.realtime.demo.EquipmentServer", fail)
    controller = DemoController(tmp_path, tmp_path / "raw/data.csv", tmp_path / "output")
    controller.thread.start()
    controller.thread.join(2)
    assert not controller.thread.is_alive()
    assert controller.snapshot()["status"] == "ERROR"
    assert "broken bundle" in controller.snapshot()["error"]


def test_loopback_http_auth_routes_and_json_validation(tmp_path):
    controller = DemoController(tmp_path, tmp_path / "raw/data.csv", tmp_path / "output")
    controller.publish(status="READY", cases=[{"id": "s"}])
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(controller, "test-token"))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=3)
    def request(method, path, body=None, headers=None):
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        return response.status, response.read()
    try:
        status, html = request("GET", "/")
        assert status == 200 and b"test-token" in html and b"__DEMO_TOKEN__" not in html
        assert request("GET", "/api/state")[0] == 200
        assert request("GET", "/../README.md")[0] == 404
        assert request("GET", "/", headers={"Host": "attacker.example"})[0] == 403
        assert request("POST", "/api/control", "{}")[0] == 403
        headers = {"X-Demo-Token": "test-token"}
        assert request("POST", "/api/control", "[]", headers)[0] == 400
        assert request("POST", "/api/control", '{"action":[]}', headers)[0] == 400
        assert request("POST", "/api/control", '{"action":"start","case":[]}', headers)[0] == 400
        assert request("POST", "/api/control", '{"action":"start","case":"s"}', headers)[0] == 202
        assert controller.commands.get_nowait() == {"action": "start", "case": "s"}
    finally:
        connection.close()
        httpd.shutdown()
        httpd.server_close()
        thread.join(2)
