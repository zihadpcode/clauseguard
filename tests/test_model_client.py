"""Live-path tests against a local fake OpenAI-compatible server, so the
real SDK request/response handling is exercised without a Meta API key."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from clauseguard import model_client

ROOT = Path(__file__).resolve().parent.parent
PLAN_A = (ROOT / "data" / "plan_a.txt").read_text(encoding="utf-8").strip()
STUB = json.loads((ROOT / "data" / "stub_responses.json").read_text(encoding="utf-8"))
PLAN_A_RESPONSE = STUB[model_client.hash_plan(PLAN_A)]["response"]


class FakeServer:
    """reject: set of (response_format type, has_temperature) combos that 400."""

    def __init__(self, reject=(), status_for_all=None, delay=0):
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append(body)
                if delay:
                    import time
                    time.sleep(delay)
                combo = (body["response_format"]["type"], "temperature" in body)
                if status_for_all:
                    return self._send(status_for_all, {"error": {"message": "nope"}})
                if combo in reject:
                    return self._send(400, {"error": {"message": f"unsupported {combo}"}})
                self._send(200, {
                    "id": "x", "object": "chat.completion", "created": 0, "model": body["model"],
                    "choices": [{"index": 0, "finish_reason": "stop",
                                 "message": {"role": "assistant", "content": json.dumps(PLAN_A_RESPONSE)}}],
                })

            def _send(self, code, payload):
                data = json.dumps(payload).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/v1"

    def close(self):
        self.httpd.shutdown()


@pytest.fixture
def live_env(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_ID", raising=False)
    servers = []

    def make(**kw):
        s = FakeServer(**kw)
        servers.append(s)
        monkeypatch.setenv("MODEL_BASE_URL", s.url)
        return s

    yield make
    for s in servers:
        s.close()


def test_strict_schema_used_when_accepted(live_env):
    server = live_env()
    result = model_client.call_model(PLAN_A)
    assert result.mode == "live"
    assert result.schema_mode == "json_schema"
    assert result.model_id == "muse-spark-1.3"
    req = server.requests[0]
    assert req["model"] == "muse-spark-1.3"
    assert req["temperature"] == 0
    assert req["response_format"]["json_schema"]["strict"] is True
    assert "<plan>" in req["messages"][1]["content"]


def test_falls_back_to_json_object_when_strict_schema_rejected(live_env):
    live_env(reject={("json_schema", True), ("json_schema", False)})
    result = model_client.call_model(PLAN_A)
    assert result.schema_mode == "json_object"
    assert len(result.raw_response["results"]) == 6


def test_temperature_rejection_is_recorded_not_hidden(live_env):
    live_env(reject={("json_schema", True)})
    result = model_client.call_model(PLAN_A)
    assert result.schema_mode == "json_schema, temperature rejected"


def test_auth_failure_is_not_masked_as_schema_fallback(live_env):
    import openai

    server = live_env(status_for_all=401)
    with pytest.raises(openai.AuthenticationError):
        model_client.call_model(PLAN_A)
    assert len(server.requests) == 1


def test_contributor_models_are_refused(live_env, monkeypatch):
    live_env()
    monkeypatch.setenv("MODEL_ID", "muse-spark-1.3-contributor")
    with pytest.raises(model_client.ModelUnavailableError):
        model_client.call_model(PLAN_A)


def test_slow_model_times_out_with_a_clear_error_instead_of_hanging(live_env, monkeypatch):
    import time

    server = live_env(delay=3)
    monkeypatch.setenv("MODEL_TIMEOUT_SECONDS", "1")
    start = time.monotonic()
    with pytest.raises(model_client.ModelUnavailableError, match="did not answer within 1 seconds"):
        model_client.call_model(PLAN_A)
    assert time.monotonic() - start < 2.5
    assert len(server.requests) == 1  # no silent retry


def test_server_error_is_not_silently_retried(live_env):
    import openai

    server = live_env(status_for_all=500)
    with pytest.raises(openai.InternalServerError):
        model_client.call_model(PLAN_A)
    assert len(server.requests) == 1


def test_timeout_setting_falls_back_on_bad_values(monkeypatch):
    for bad in ("abc", "0", "-5"):
        monkeypatch.setenv("MODEL_TIMEOUT_SECONDS", bad)
        assert model_client.timeout_seconds() == model_client.DEFAULT_TIMEOUT_SECONDS
    monkeypatch.setenv("MODEL_TIMEOUT_SECONDS", "90")
    assert model_client.timeout_seconds() == 90
