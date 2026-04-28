from villanibench.harness.notes import append_note


def test_append_note_preserves_existing_and_appends():
    out = append_note("runner crash note", "preflight stderr")
    assert out == "runner crash note\npreflight stderr"


def test_append_note_bounds_long_output():
    existing = "a" * 1900
    note = "b" * 500
    out = append_note(existing, note, limit=2000)
    assert out is not None
    assert len(out) == 2000
    assert out.startswith("a" * 100)
