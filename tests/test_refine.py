import json

from voicenotes.models import Insights
from voicenotes.refine import Refiner, insights_from_dict, parse_json_object

from .fakes import FakeLLM


def test_parse_json_object_tolerates_fences_and_chatter():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('Sure! {"a": 2} hope it helps') == {"a": 2}


def test_insights_from_dict_normalises():
    i = insights_from_dict({"title": '"Plan"', "key_points": "one", "action_items": ["- Call bank", "call bank", ""]})
    assert i == Insights(title="Plan", key_points=["one"], action_items=["Call bank"])


def test_clean_returns_llm_edit():
    llm = FakeLLM(lambda s, p, f: "I went to the bank today and paid the bill.")
    out = Refiner(llm).clean("i go to bank today and pay the bill")
    assert out == "I went to the bank today and paid the bill."
    assert "Preserve EVERY idea" in llm.calls[0]["system"]


def test_clean_rejects_summaries():
    text = " ".join(["This is a long detailed sentence about my plans."] * 20)
    r = Refiner(FakeLLM(lambda s, p, f: "Plans."))
    assert r.clean(text) == text
    assert r.warnings


def test_insights_single_chunk():
    payload = {"title": "Week plan", "key_points": ["Plan week"], "action_items": ["Call the bank"]}
    llm = FakeLLM(lambda s, p, f: json.dumps(payload))
    i = Refiner(llm).insights("I need to call the bank.")
    assert i.action_items == ["Call the bank"]
    assert llm.calls[0]["format"]["type"] == "object"


def test_insights_multi_chunk_merges():
    def responder(system, prompt, fmt):
        if "Merge" in system:
            return json.dumps({"title": "Merged", "key_points": ["A", "B"], "action_items": ["Task 1", "Task 2"]})
        n = len([c for c in llm.calls if "Merge" not in c["system"]])
        return json.dumps({"title": f"T{n}", "key_points": [f"P{n}"], "action_items": [f"Task {n}"]})

    llm = FakeLLM(responder)
    text = " ".join(f"Sentence {i} about something important." for i in range(400))
    i = Refiner(llm, chunk_chars=1000).insights(text)
    assert i.title == "Merged"
    assert any("Merge" in c["system"] for c in llm.calls)


def test_insights_merge_cannot_drop_tasks():
    def responder(system, prompt, fmt):
        if "Merge" in system:
            return json.dumps({"title": "M", "key_points": [], "action_items": []})
        return json.dumps({"title": "T", "key_points": [], "action_items": [f"Task {len(llm.calls)}"]})

    llm = FakeLLM(responder)
    text = " ".join(f"Sentence {i} about something important." for i in range(400))
    i = Refiner(llm, chunk_chars=1000).insights(text)
    assert len(i.action_items) >= 2


def test_insights_bad_json_warns():
    r = Refiner(FakeLLM(lambda s, p, f: "not json"))
    assert r.insights("text") == Insights()
    assert r.warnings
