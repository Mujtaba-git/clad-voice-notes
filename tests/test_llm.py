import json

import httpx
import pytest

from voicenotes.llm import LLMError, OllamaClient, strip_thinking


def client(handler):
    return OllamaClient(model="m:1b", transport=httpx.MockTransport(handler))


def test_chat_sends_messages_and_returns_content():
    seen = {}

    def handler(req):
        seen.update(json.loads(req.content))
        return httpx.Response(200, json={"message": {"content": " hi "}})

    out = client(handler).chat("hello", system="sys", format={"type": "object"})
    assert out == "hi"
    assert seen["model"] == "m:1b" and seen["stream"] is False
    assert seen["messages"][0] == {"role": "system", "content": "sys"}
    assert seen["format"] == {"type": "object"}


def test_chat_strips_thinking():
    c = client(lambda r: httpx.Response(200, json={"message": {"content": "<think>hmm</think>Answer"}}))
    assert c.chat("q") == "Answer"
    assert strip_thinking("a<think>\nx\n</think> b") == "a b"


def test_missing_model_gives_helpful_error():
    c = client(lambda r: httpx.Response(404, json={"error": "model not found"}))
    with pytest.raises(LLMError, match="ollama pull m:1b"):
        c.chat("q")


def test_unreachable_server():
    def boom(req):
        raise httpx.ConnectError("refused")

    c = client(boom)
    assert c.is_available() is False
    with pytest.raises(LLMError, match="running"):
        c.chat("q")


def test_has_model():
    c = client(lambda r: httpx.Response(200, json={"models": [{"name": "m:1b"}, {"name": "x:latest"}]}))
    assert c.has_model()
    c.model = "x"
    assert c.has_model()
    c.model = "y"
    assert not c.has_model()
