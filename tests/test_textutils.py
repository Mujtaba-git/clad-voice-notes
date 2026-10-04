from voicenotes.textutils import chunk_text, split_sentences, word_count


def test_split_english_and_urdu_punctuation():
    text = "Hello there. How are you? آج موسم اچھا ہے۔ کیا تم آؤ گے؟ Done!"
    assert split_sentences(text) == [
        "Hello there.", "How are you?", "آج موسم اچھا ہے۔", "کیا تم آؤ گے؟", "Done!",
    ]


def test_split_empty():
    assert split_sentences("   ") == []


def test_chunk_keeps_sentences_whole_and_loses_nothing():
    sents = [f"Sentence number {i} is here." for i in range(50)]
    text = " ".join(sents)
    chunks = chunk_text(text, max_chars=120)
    assert all(len(c) <= 120 for c in chunks)
    assert " ".join(chunks) == text
    for c in chunks:
        assert c.endswith(".")


def test_chunk_hard_splits_overlong_sentence():
    text = " ".join(["word"] * 100)  # no punctuation, 499 chars
    chunks = chunk_text(text, max_chars=50)
    assert all(len(c) <= 50 for c in chunks)
    assert " ".join(chunks) == text


def test_word_count():
    assert word_count("one two  three") == 3
