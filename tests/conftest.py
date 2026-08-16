import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.schema import Chunk, Document  # noqa: E402


@pytest.fixture
def doc() -> Document:
    return Document(
        doc_id="abc123",
        model="Galaxy S24 Ultra",
        title="Galaxy S24 Ultra User Manual",
        url="https://example.com/s24u.pdf",
        sha256="abc123",
        n_pages=180,
        language="en",
        region="US",
        os_version="One UI 6.1",
    )


@pytest.fixture
def chunks(doc) -> list[Chunk]:
    return [
        Chunk(
            doc_id=doc.doc_id,
            text="To enable Always On Display, go to Settings, tap Lock screen, "
            "then tap Always On Display.",
            section_path="Settings > Lock screen",
            page_start=42,
            page_end=42,
            token_count=20,
        ),
        Chunk(
            doc_id=doc.doc_id,
            text="Fast charging requires a 45W adapter, model EP-TA845.",
            section_path="Settings > Battery > Charging",
            page_start=57,
            page_end=58,
            token_count=12,
        ),
        Chunk(
            doc_id=doc.doc_id,
            text="Bixby Routines can automate device actions based on conditions.",
            section_path="Apps > Bixby",
            page_start=99,
            page_end=99,
            token_count=11,
        ),
    ]
