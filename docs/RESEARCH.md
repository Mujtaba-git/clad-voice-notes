# Research summary (October 2026)

## 1. Existing products

| Product | Local? | Free? | Urdu→English notes? | Notes |
|---|---|---|---|---|
| Google Translate (current workflow) | ❌ cloud | ✅ | partial | Live speech translation, but you copy/paste manually; no cleanup or to-dos |
| Wispr Flow, Superwhisper, MacWhisper Pro | mostly | ❌ paid | ❌ | Dictation into the cursor, English-centric |
| Otter, Fireflies, Notion AI | ❌ cloud | ❌ paid | ❌ | Meeting notes; weak Urdu |
| Obsidian plugins (Whisper, Smart Connections) | via API | API credits | ❌ | Need OpenAI keys |

## 2. Open-source projects on GitHub

| Project | What it is | Why not use it as the base |
|---|---|---|
| [OpenWhispr](https://openwhispr.com) | Electron dictation app, local Whisper + optional LLM polish | Built for short dictation into other apps, not hour-long notes; heavy Electron stack |
| [FlowSpeech](https://github.com/N23eos/flowspeech) | macOS hold-to-talk dictation, faster-whisper + LLM cleanup | Push-to-talk snippets; no translation, notes or to-dos |
| [Kalamos](https://github.com/xmasyx/kalamos) | macOS local dictation, Whisper on the Neural Engine + local LLM | Same: cursor dictation, English focus |
| [local-whisper](https://github.com/luisalima/local-whisper) | whisper.cpp dictation tool | Dictation only |
| VoiceInk, Buzz, Handy | Whisper front-ends | Transcription only; no Urdu→English refinement pipeline |

**Conclusion:** all of these solve *dictation* (a few seconds of speech into a text box).
Your need is different: **long-form thinking aloud in Urdu, then faithful English, then
structured notes in Obsidian**. Forking a dictation app would mean removing most of it and
adding all of the hard parts. So VoiceNotes reuses the proven *engines*
(Whisper via `mlx-whisper`/`faster-whisper`/`sherpa-onnx`, Ollama, ffmpeg, FastAPI) and only
adds the thin glue that is specific to you. The app itself is about 1,500 lines.

## 3. Speech recognition for Urdu

- **Whisper** (OpenAI, MIT licence) supports Urdu, punctuation and Urdu/English code-switching.
  Published Urdu benchmarks (FLEURS / Common Voice) report error rates falling sharply with model
  size: tiny ~67% WER, base ~54%, small ~34%. Large-v3 and its fine-tunes are much better.
  → **Default `large-v3-turbo`** (near large-v3 accuracy, ~8× faster). **`large-v3`** is the
  accuracy option.
- Urdu fine-tunes of Whisper exist on Hugging Face (e.g. `whisper-medium-urdu`, ~27% WER on
  Common Voice). They can be plugged in through the model setting (an MLX/CT2 conversion is needed).
- **wav2vec2-xls-r-300m-urdu**: no punctuation and weaker on mixed English, so not chosen.
- Measured in this repo: Whisper `small` gets the Urdu test clip almost word-perfect in Urdu
  script, and the English clip exactly.

## 4. Translation options

| Option | Quality on our Urdu clip | Cost | Offline |
|---|---|---|---|
| Whisper `task=translate` (small) | Loses meaning: "loan application" → "duty of Friday" | free | ✅ |
| Google Translate on the transcript | Fluent, but translates recognition errors literally ("bang", "wallet") | free (unofficial) | ❌ |
| Local LLM on the transcript (Gemma 3 / Qwen 3) | Fluent; prompted to infer misrecognised words; handles mixed English | free | ✅ |
| Meta NLLB-200 / SeamlessM4T | Good sentence MT, but CC-BY-NC, no context, extra 2–5 GB model | free | ✅ |

→ **Default: local LLM.** Google is offered as an opt-in, and Whisper as the zero-setup fallback.

## 5. Local LLM choice

For an **M3 Pro (18 GB+ unified memory)**, models that run comfortably through Ollama at 4-bit:

| Model | RAM | Notes |
|---|---|---|
| `gemma3:12b` (**default**) | ~8 GB | Strong multilingual coverage (140+ languages), good instruction following, no "thinking" output |
| `qwen3:8b` / `qwen3:14b` | 5–10 GB | Strong multilingual; thinking blocks are stripped automatically |
| `gemma3:4b` | ~3 GB | Light option when memory is tight |
| `gemma3:27b` | ~17 GB | Best quality; needs 32 GB+ RAM |

The model is a setting, so newer models can be adopted with `ollama pull` and no code change.

## Sources

- [OpenWhispr](https://openwhispr.com/use-cases/mac), [FlowSpeech](https://github.com/N23eos/flowspeech), [Kalamos](https://github.com/xmasyx/kalamos), [local-whisper](https://github.com/luisalima/local-whisper), [VoiceScribe](https://gitblind.noratr.app/eddmann/VoiceScribe)
- Urdu ASR benchmarks: [arXiv 2508.09865](https://arxiv.org/abs/2508.09865v1), [whisper-medium-urdu](https://www.promptlayer.com/models/whisper-medium-urdu), [wav2vec2 Urdu review](https://aiindigo.com/blog/honest-review-wav2vec2-large-xls-r-300m-urdu-2026)
- LLMs for Urdu: [SiliconFlow guide](https://www.siliconflow.com/articles/best-open-source-llm-for-urdu), [best Ollama models 2026](https://toolhalla.ai/blog/best-ollama-models-2026)
