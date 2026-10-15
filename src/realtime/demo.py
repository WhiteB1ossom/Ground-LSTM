"""Loopback presentation demo: synthetic observations through the actual server models."""

import argparse
from collections import deque
from copy import deepcopy
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import queue
import secrets
import threading
import time
import webbrowser

from src.realtime.equipment_server import EquipmentServer, TASKS
from src.realtime.replay import observations
from src.realtime.stream import RealtimePipeline
from src.realtime.timeline import TimelineWriter


DEFAULT_RUN = Path("artifacts/server-equipment-20261015")
DEFAULT_INPUT = Path("data/raw/equipment-server/server-equipment-20261015/heldout.synthetic.csv")
SPEEDS = (1, 5, 10, 20)
SCENARIOS = {
    "normal": ("정상", "정상 입력에서 두 점검 경보가 유지되지 않는지 확인합니다."),
    "surge_only": ("서지만 발생", "65·105·145초에 합성 카운터가 증가합니다. 서지 활동 점수와 경보를 봅니다."),
    "heating_without_surge": ("서지 없는 발열", "60초부터 관측 온도가 상승합니다. 서지 없이 장비 점검 경보가 생기는지 봅니다."),
    "both": ("발열 + 서지", "60초의 온도 변화와 65초의 카운터 증가를 두 모델이 따로 판단합니다."),
    "counter_reset": ("카운터 리셋", "90초에 누적값이 감소합니다. 이를 새 서지 증가로 세지 않는지 확인합니다."),
}


def load_cases(path, sensors):
    """Keep complete acquisitions, including initial slow-sensor observations."""
    cases = {}
    for row in observations(path, sensors):
        if str(row.get("is_synthetic", "")).lower() != "true" or row.get("acquisition_kind") != "synthetic":
            raise ValueError("The presentation demo accepts explicitly synthetic acquisitions only")
        session = row.get("session_id")
        if not session:
            raise ValueError("Demo input requires acquisition session_id")
        case = cases.setdefault(session, {"id": session, "scenario": row.get("scenario", ""), "rows": []})
        if case["scenario"] != row.get("scenario", ""):
            raise ValueError("Scenario must remain constant within a demo acquisition")
        case["rows"].append(row)
    if not cases:
        raise ValueError("No demo observations")
    for case in cases.values():
        stamps = [datetime.fromisoformat(r["timestamp"]) for r in case["rows"]]
        if any(s.tzinfo is None for s in stamps) or any(b <= a for a, b in zip(stamps, stamps[1:])):
            raise ValueError("Demo timestamps must be timezone-aware and strictly increasing per acquisition")
        case["times"] = [(s - stamps[0]).total_seconds() for s in stamps]
    return cases


class DemoSession:
    """Owned by one worker; browser threads only read detached snapshots."""

    def __init__(self, server, case, output):
        self.server, self.case, self.output = server, case, output
        # Selecting a case explicitly starts a separate acquisition. Truth labels
        # never reset preprocessing; loaded immutable models/scalers are reused.
        server.pipelines = {t: RealtimePipeline(p.engine, deepcopy(p.settings)) for t, p in server.pipelines.items()}
        output.mkdir(parents=True, exist_ok=False)
        self.writer = TimelineWriter(output)
        self.index = 0
        self.latest = None
        self.predictions = {}
        self.inferences = {t: 0 for t in TASKS}
        self.history, self.events = deque(maxlen=360), deque(maxlen=50)
        self.closed = False
        self.failures = 0
        self.event("새 합성 획득 세션 · 버퍼 시작")

    def event(self, text):
        seconds = self.case["times"][max(0, self.index - 1)]
        self.events.append({"seconds": seconds, "text": text})

    @property
    def done(self):
        return self.index >= len(self.case["rows"])

    @property
    def warming(self):
        return any(p.ring.size < p.builder.length for p in self.server.pipelines.values())

    def step(self):
        if self.closed or self.done:
            raise RuntimeError("Demo acquisition is not running")
        source = self.case["rows"][self.index]
        rows = self.server.feed(source)
        self.index += 1
        for row in rows:
            if not self.writer.write(row):
                raise OSError("Demo timeline could not be saved")
            self.latest = row
            fresh = False
            for task in TASKS:
                record = row["tasks"][task]
                if record["prediction"]:
                    self.predictions[task] = {**record["prediction"], "timestamp": row["timestamp"]}
                    self.inferences[task] += 1
                    if self.inferences[task] == 1:
                        self.event(f"{task} · 첫 실제 LSTM 추론")
                    fresh = True
                decision = record["decision"]
                if decision["transition"]:
                    self.event(f"{task} · {decision['transition']} · {decision['reason']}")
                if decision["reason"].startswith(("INFERENCE_ERROR:", "PREPROCESSING_ERROR:")):
                    self.failures += 1
                    self.event(f"{task} · {decision['reason']}")
            if row["equipment"]["counter"]["reset"]:
                self.event("카운터 리셋 · 감소를 신규 서지로 세지 않음")
            if fresh:
                self.history.append({"seconds": self.case["times"][self.index - 1],
                                     **{t: self.predictions.get(t, {}).get("risk_score") for t in TASKS}})

    def snapshot(self):
        row = self.latest
        pipeline = self.server.pipelines["degradation"]
        tasks = {}
        for task, p in self.server.pipelines.items():
            record = row["tasks"][task] if row else None
            tasks[task] = {"prediction": self.predictions.get(task), "inferences": self.inferences[task],
                           "available": record["available"] if record else False,
                           "alarm_active": record["decision"]["alarm_active"] if record else False,
                           "reason": record["decision"]["reason"] if record else "WARMING_UP",
                           "threshold_on": p.decision.on, "threshold_off": p.decision.off,
                           "consecutive": p.decision.consecutive, "model_version": p.engine.manifest["model_version"]}
        return deepcopy({"session_id": self.case["id"], "scenario": self.case["scenario"],
                         "progress": self.index, "total": len(self.case["rows"]),
                         "seconds": self.case["times"][max(0, self.index - 1)], "duration": self.case["times"][-1],
                         "timestamp": row["timestamp"] if row else None,
                         "state": row["state"] if row else "UNAVAILABLE", "tasks": tasks,
                         "ring": {"size": pipeline.ring.size, "capacity": pipeline.ring.capacity,
                                  "window": pipeline.builder.length, "features": pipeline.ring.feature_count,
                                  "stride": pipeline.builder.stride, "overwritten": pipeline.ring.overwritten_samples},
                         "physical_values": row["tasks"]["degradation"]["physical_values"] if row else {},
                         "observation_age_seconds": row["tasks"]["degradation"]["observation_age_seconds"] if row else [],
                         "criteria": row["maintenance_criteria"] if row else {},
                         "equipment": row["equipment"] if row else {}, "history": list(self.history),
                         "events": list(self.events), "output": str(self.output), "processing_failures": self.failures})

    def close(self, outcome):
        if self.closed:
            return
        self.closed = True
        trace = self.writer.close()
        summary = {"status": "DEGRADED" if self.failures or trace["error_count"] else outcome,
                   "synthetic_demo": True, "session_id": self.case["id"], "scenario": self.case["scenario"],
                   "observations": self.index, "inferences": self.inferences, "timeline": trace,
                   "processing_failure_count": self.failures, "physical_validation": False,
                   "hardware_actuation_performed": False}
        (self.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        if trace["error_count"]:
            raise OSError("Demo timeline save failed")


class DemoController:
    def __init__(self, run, input_path, output):
        self.run, self.input, self.output = run, input_path, output
        if output.resolve().is_relative_to(input_path.resolve().parent):
            raise ValueError("Demo output must be outside raw inputs")
        self.commands = queue.Queue(maxsize=32)
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.state = {"status": "LOADING", "error": None, "cases": [], "speed": 10, "demo": None,
                      "synthetic_demo": True, "hardware_actuation_performed": False}
        self.thread = threading.Thread(target=self._work, name="demo-model-owner", daemon=True)

    def snapshot(self):
        with self.lock:
            return deepcopy(self.state)

    def publish(self, **values):
        with self.lock:
            self.state.update(values)

    def control(self, message):
        if (not isinstance(message, dict) or not isinstance(message.get("action"), str)
                or message["action"] not in {"start", "pause", "resume", "speed"}):
            raise ValueError("Unknown demo action")
        message = deepcopy(message)
        state = self.snapshot()
        if state["status"] in {"LOADING", "ERROR"}:
            raise ValueError("Models are not ready; see demo status")
        if message["action"] == "start" and (not isinstance(message.get("case"), str)
                                             or message["case"] not in {c["id"] for c in state["cases"]}):
            raise ValueError("Unknown acquisition")
        if message["action"] == "speed" and (type(message.get("value")) is not int or message["value"] not in SPEEDS):
            raise ValueError("Speed must be 1, 5, 10 or 20")
        try:
            self.commands.put_nowait(message)
        except queue.Full as error:
            raise ValueError("Demo control queue is busy") from error

    def _work(self):
        session, status, speed, due = None, "READY", 10, 0.
        try:
            server = EquipmentServer(self.run)
            sensors = [s.name for s in server.pipelines["degradation"].sensors if s.enabled]
            cases = load_cases(self.input, sensors)
            catalog = []
            for c in sorted(cases.values(), key=lambda c: list(SCENARIOS).index(c["scenario"]) if c["scenario"] in SCENARIOS else len(SCENARIOS)):
                name, hint = SCENARIOS.get(c["scenario"], (c["scenario"], "전체 합성 Test 획득 세션을 재생합니다."))
                catalog.append({"id": c["id"], "scenario": c["scenario"], "name": name, "hint": hint, "rows": len(c["rows"])})
            self.publish(status=status, cases=catalog)
            while not self.stop_event.is_set():
                timeout = max(0., min(.1, due - time.monotonic())) if status == "RUNNING" else .1
                try:
                    command = self.commands.get(timeout=timeout)
                except queue.Empty:
                    command = None
                if command:
                    action = command["action"]
                    if action == "start":
                        if session:
                            session.close("INTERRUPTED")
                        destination = self.output / (datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-" + secrets.token_hex(3))
                        session = DemoSession(server, cases[command["case"]], destination)
                        status, due = "RUNNING", time.monotonic()
                    elif action == "pause" and status == "RUNNING":
                        status = "PAUSED"
                    elif action == "resume" and status == "PAUSED":
                        status, due = "RUNNING", time.monotonic()
                    elif action == "speed":
                        speed = command["value"]
                        due = time.monotonic()
                if status == "RUNNING" and time.monotonic() >= due:
                    session.step()
                    if session.done:
                        session.event("전체 합성 획득 세션 재생 완료")
                        session.close("COMPLETE")
                        status = "FINISHED"
                    else:
                        delta = session.case["times"][session.index] - session.case["times"][session.index - 1]
                        due += delta / (1 if session.warming else speed)
                self.publish(status=status, speed=speed, effective_speed=1 if session and session.warming else speed,
                             demo=session.snapshot() if session else None)
        except Exception as error:
            # Surface failures to the audience and keep the last known snapshot.
            self.publish(status="ERROR", error=f"{type(error).__name__}: {error}")
        finally:
            if session and not session.closed:
                try:
                    session.close("ERROR" if self.snapshot()["status"] == "ERROR" else "INTERRUPTED")
                except Exception as error:
                    self.publish(status="ERROR", error=f"Save failed: {error}")


def make_handler(controller, token):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def local_host(self):
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            if self.headers.get("Host", "") not in allowed:
                self.respond(403, b'{"error":"Local host required"}')
                return False
            return True

        def log_message(self, *_args):
            pass

        def respond(self, status, payload, content_type="application/json; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            if not self.local_host():
                return
            if self.path == "/":
                html = Path(__file__).with_name("demo.html").read_text(encoding="utf-8").replace("__DEMO_TOKEN__", token)
                self.respond(200, html.encode("utf-8"), "text/html; charset=utf-8")
            elif self.path == "/api/state":
                self.respond(200, json.dumps(controller.snapshot(), ensure_ascii=False, allow_nan=False).encode("utf-8"))
            else:
                self.respond(404, b'{"error":"Not found"}')

        def do_POST(self):
            if not self.local_host():
                return
            if self.path != "/api/control":
                self.respond(404, b'{"error":"Not found"}')
                return
            if not secrets.compare_digest(self.headers.get("X-Demo-Token", ""), token):
                self.respond(403, b'{"error":"Invalid local demo token"}')
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 2048:
                    raise ValueError("Invalid control size")
                controller.control(json.loads(self.rfile.read(length)))
            except (ValueError, UnicodeError) as error:
                self.respond(400, json.dumps({"error": str(error)}).encode("utf-8"))
                return
            self.respond(202, b'{"accepted":true}')

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=Path("artifacts/presentation-demo"))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="Open the local presentation page")
    args = parser.parse_args(argv)
    controller = DemoController(args.run, args.input, args.output)
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(controller, secrets.token_hex(32)))
    httpd.daemon_threads = True
    controller.thread.start()
    url = f"http://127.0.0.1:{httpd.server_port}"
    print(f"Presentation demo: {url}\nActual LSTM inference; synthetic Test input. Ctrl+C to stop.", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        httpd.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        controller.stop_event.set()
        controller.thread.join(timeout=10)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
