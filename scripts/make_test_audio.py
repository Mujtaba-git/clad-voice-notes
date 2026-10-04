"""Generate small speech fixtures for the test-suite.

Uses Google's free translate TTS endpoint (no key needed) to synthesise
Urdu and English sentences, then ffmpeg to join them into 16 kHz mono WAV.
Run: python scripts/make_test_audio.py
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "audio"

CLIPS = {
    "english_todo": (
        "en",
        [
            "Today I want to plan the week for my new project.",
            "First, I need to call the bank about the loan application.",
            "Second, I should finish the presentation for Monday's meeting.",
            "And finally, remember to buy groceries in the evening.",
        ],
    ),
    "urdu_todo": (
        "ur",
        [
            "آج میں اپنے نئے کاروبار کے بارے میں سوچ رہا تھا۔",
            "مجھے کل صبح بینک جا کر قرض کی درخواست جمع کروانی ہے۔",
            "اس کے علاوہ مجھے اپنی بہن کو فون کرنا ہے۔",
            "اور شام کو بازار سے سبزی خریدنی ہے۔",
        ],
    ),
    "urdu_mixed": (
        "ur",
        [
            "میں ایک ایسی ایپلیکیشن بنانا چاہتا ہوں جو میری آواز کو ٹیکسٹ میں بدل دے۔",
            "اس کا مقصد یہ ہے کہ میں اپنے آئیڈیاز کو آسانی سے نوٹ کر سکوں۔",
        ],
    ),
}


def tts(text: str, lang: str, dest: Path) -> None:
    q = urllib.parse.urlencode({"ie": "UTF-8", "client": "gtx", "tl": lang, "q": text})
    req = urllib.request.Request(
        f"https://translate.googleapis.com/translate_tts?{q}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        dest.write_bytes(r.read())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, (lang, sentences) in CLIPS.items():
        with tempfile.TemporaryDirectory() as td:
            parts = []
            for i, s in enumerate(sentences):
                p = Path(td) / f"{i}.mp3"
                tts(s, lang, p)
                parts.append(p)
            lst = Path(td) / "list.txt"
            lst.write_text("".join(f"file '{p}'\n" for p in parts))
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                 "-i", str(lst), "-ar", "16000", "-ac", "1", str(OUT / f"{name}.wav")],
                check=True,
            )
        manifest[name] = {"language": lang, "text": " ".join(sentences)}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("wrote", ", ".join(manifest))


if __name__ == "__main__":
    main()
