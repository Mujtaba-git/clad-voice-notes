import httpx
import pytest

from voicenotes.translate import GoogleTranslator, LLMTranslator, TranslationError

from .fakes import FakeLLM


def test_llm_translator_chunks_and_passes_context():
    llm = FakeLLM(lambda s, p, f: f"EN[{p.split(':')[-1].strip()[:10]}]")
    text = "۔ ".join(["یہ ایک لمبا جملہ ہے"] * 40) + "۔"
    out = LLMTranslator(llm, chunk_chars=200).translate(text)
    assert len(llm.calls) > 1
    assert "Urdu-to-English" in llm.calls[0]["system"]
    assert "previous part" not in llm.calls[0]["prompt"]
    assert "previous part" in llm.calls[1]["prompt"]
    assert out.count("EN[") == len(llm.calls)


def test_llm_translator_rejects_empty_output():
    with pytest.raises(TranslationError):
        LLMTranslator(FakeLLM(lambda s, p, f: "  ")).translate("کچھ")


def test_google_translator_parses_response():
    def handler(req):
        assert req.url.params["sl"] == "ur" and req.url.params["tl"] == "en"
        return httpx.Response(200, json=[[["Hello. ", "سلام۔"], ["World.", "دنیا۔"]], None, "ur"])

    g = GoogleTranslator(transport=httpx.MockTransport(handler))
    assert g.translate("سلام۔ دنیا۔") == "Hello. World."


def test_google_translator_retries_then_fails():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(429)

    g = GoogleTranslator(retries=2, transport=httpx.MockTransport(handler), sleep=lambda s: None)
    with pytest.raises(TranslationError, match="429"):
        g.translate("سلام")
    assert len(calls) == 3


def test_google_translator_recovers_after_rate_limit():
    responses = iter([httpx.Response(429), httpx.Response(200, json=[[["Hi", "سلام"]]])])
    g = GoogleTranslator(transport=httpx.MockTransport(lambda r: next(responses)), sleep=lambda s: None)
    assert g.translate("سلام") == "Hi"
