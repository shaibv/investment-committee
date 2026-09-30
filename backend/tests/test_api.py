import json

from fastapi.testclient import TestClient

from committee.api import app

client = TestClient(app)


def test_config_lists_mock_provider_and_candidates() -> None:
    body = client.get("/api/config").json()
    assert "mock" in body["providers"]
    assert len(body["candidates"]) > 0


def test_stream_emits_events_then_a_result() -> None:
    with client.stream("GET", "/api/runs/stream?provider=mock&data=synthetic") as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        messages = [
            json.loads(line.removeprefix("data: "))
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]
    kinds = [m["kind"] for m in messages]
    assert kinds[-1] == "result"
    assert "event" in kinds
    assert messages[-1]["result"]["portfolio"]["total_value"] == 100_000
