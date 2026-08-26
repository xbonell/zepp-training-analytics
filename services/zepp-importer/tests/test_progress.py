from fitness.progress import ProgressEvent, emit


def test_emit_invokes_callback():
    seen: list[ProgressEvent] = []
    event = ProgressEvent(phase="history", current=1, total=None, message="start")
    emit(seen.append, event)
    assert seen == [event]


def test_emit_none_is_noop():
    event = ProgressEvent(phase="history", current=1, total=None)
    emit(None, event)  # must not raise
