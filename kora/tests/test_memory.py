import pytest

import eval_recall
from memory import MemoryNotFound, MemoryStore, SecretDetected


def test_add_and_get(store):
    mid = store.add("My systems design exam is on 3 November", kind="event")
    memory = store.get(mid)
    assert memory["text"] == "My systems design exam is on 3 November"
    assert memory["kind"] == "event"
    assert memory["source"] == "user"


def test_recall_finds_related_memory_first(store):
    store.add("I prefer Flutter for mobile and React for web")
    exam = store.add("My systems design exam is on 3 November")
    assert store.recall("When is my exam?")[0][0]["id"] == exam


def test_recall_returns_nothing_for_unrelated_question(store):
    store.add("My systems design exam is on 3 November")
    assert store.recall("What is the capital of Peru?") == []


def test_secret_is_rejected_and_logged(store):
    with pytest.raises(SecretDetected):
        store.add("my password is hunter2")
    assert store.latest() == []
    assert store.audit()[0]["action"] == "rejected_secret"


def test_edit_updates_text_and_meaning(store):
    mid = store.add("My exam is on 3 November")
    store.edit(mid, "My group presentation is next Friday")
    assert store.get(mid)["text"] == "My group presentation is next Friday"
    assert store.recall("When do we present the team project?")[0][0]["id"] == mid


def test_edit_rejects_secret(store):
    mid = store.add("My exam is on 3 November")
    with pytest.raises(SecretDetected):
        store.edit(mid, "my password is hunter2")
    assert store.get(mid)["text"] == "My exam is on 3 November"


def test_forget_removes_memory(store):
    mid = store.add("I deployed the attendance app on Contabo with Docker")
    store.forget(mid)
    with pytest.raises(MemoryNotFound):
        store.get(mid)
    assert store.recall("Where is the attendance app deployed?") == []


def test_unknown_ids_raise(store):
    with pytest.raises(MemoryNotFound):
        store.forget(999)
    with pytest.raises(MemoryNotFound):
        store.edit(999, "anything")


def test_audit_log_never_contains_memory_text(store):
    mid = store.add("I adopted a purple zebra named Biko")
    store.recall("zebra")
    store.forget(mid)
    for row in store.audit():
        assert "zebra" not in str(row["detail"]).lower()


def test_forgotten_text_is_wiped_from_disk(tmp_path, model):
    path = tmp_path / "kora.db"
    store = MemoryStore(str(path), model=model)
    mid = store.add("I adopted a purple zebra named Biko")
    store.forget(mid)
    store.db.close()
    assert b"purple zebra" not in path.read_bytes()


def test_memories_survive_restart(tmp_path, model):
    path = str(tmp_path / "kora.db")
    first = MemoryStore(path, model=model)
    mid = first.add("My exam is on 3 November")
    first.db.close()
    second = MemoryStore(path, model=model)
    assert second.get(mid)["text"] == "My exam is on 3 November"
    second.db.close()


def test_recall_quality_on_eval_set(store):
    ids = [store.add(text) for text in eval_recall.MEMORIES]
    answers = [(store.recall(q, k=1), ids[i]) for q, i in eval_recall.RELATED]
    right = sum(1 for results, expected in answers if results and results[0][0]["id"] == expected)
    wrong = sum(1 for results, expected in answers if results and results[0][0]["id"] != expected)
    false_alarms = sum(1 for q in eval_recall.UNRELATED if store.recall(q, k=1))
    # Measured 15/17 right, 0 wrong, 0 false alarms when the thresholds were tuned.
    assert right >= 14
    assert wrong == 0
    assert false_alarms == 0
