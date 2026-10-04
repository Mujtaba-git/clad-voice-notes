"""Real local-LLM checks. Needs a running Ollama with the model pulled:
    ollama pull $VOICENOTES_TEST_LLM   (default: gemma3:1b, small enough for CI)
Skipped automatically when Ollama is not reachable."""
import os

import pytest

from voicenotes.llm import OllamaClient
from voicenotes.refine import Refiner
from voicenotes.translate import LLMTranslator

MODEL = os.environ.get("VOICENOTES_TEST_LLM", "gemma3:1b")
URDU = ("آج میں اپنے نئے کاروبار کے بارے میں سوچ رہا تھا۔ مجھے کل صبح بینک جا کر قرض کی درخواست جمع کروانی ہے۔ "
        "اس کے علاوہ مجھے اپنی بہن کو فون کرنا ہے۔ اور شام کو بازار سے سبزی خریدنی ہے۔")


@pytest.fixture(scope="module")
def llm():
    c = OllamaClient(model=MODEL, timeout=300)
    if not c.is_available() or not c.has_model():
        pytest.skip(f"Ollama with {MODEL} not available")
    return c


@pytest.mark.integration
def test_llm_translates_urdu(llm):
    en = LLMTranslator(llm).translate(URDU).lower()
    print(en)
    assert "bank" in en and "sister" in en


@pytest.mark.integration
def test_llm_cleans_and_extracts_tasks(llm):
    r = Refiner(llm)
    text = ("so today i was thinking um about my new business and uh tomorrow morning i have to go "
            "to bank for submit the loan application, also i have to call to my sister and in evening "
            "buy vegetables from market")
    clean = r.clean(text)
    print(clean)
    assert "bank" in clean.lower() and "sister" in clean.lower()
    ins = r.insights(clean)
    print(ins)
    assert ins.action_items, ins
    assert any("bank" in a.lower() or "loan" in a.lower() for a in ins.action_items)
