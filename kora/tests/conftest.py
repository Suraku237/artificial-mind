import pytest
from sentence_transformers import SentenceTransformer

from memory import MODEL_NAME, MemoryStore


@pytest.fixture(scope="session")
def model():
    # Loaded once for the whole run; loading per test would take minutes.
    return SentenceTransformer(MODEL_NAME, device="cpu")


@pytest.fixture
def store(model):
    s = MemoryStore(":memory:", model=model)
    yield s
    s.db.close()
