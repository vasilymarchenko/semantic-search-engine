"""Unit tests for Trajectory-2 data models."""

from __future__ import annotations

import hashlib

import pytest

from semantic_search.models_v2 import (
    ExternalItem,
    ProcessedContent,
    RawContent,
    url_hash,
)


# ---------------------------------------------------------------------------
# url_hash
# ---------------------------------------------------------------------------


def test_url_hash_is_deterministic() -> None:
    assert url_hash("https://example.com") == url_hash("https://example.com")


def test_url_hash_length() -> None:
    assert len(url_hash("https://example.com")) == 16


def test_url_hash_hex() -> None:
    h = url_hash("https://example.com")
    int(h, 16)  # raises ValueError if not valid hex


def test_url_hash_different_urls_produce_different_hashes() -> None:
    assert url_hash("https://example.com/a") != url_hash("https://example.com/b")


def test_url_hash_matches_sha256() -> None:
    url = "https://example.com"
    expected = hashlib.sha256(url.encode()).hexdigest()[:16]
    assert url_hash(url) == expected


# ---------------------------------------------------------------------------
# RawContent
# ---------------------------------------------------------------------------


def test_raw_content_minimal() -> None:
    rc = RawContent(text="hello world")
    assert rc.text == "hello world"
    assert rc.title is None
    assert rc.metadata == {}


def test_raw_content_frozen() -> None:
    rc = RawContent(text="hello")
    with pytest.raises(Exception):  # ValidationError or AttributeError depending on mode
        rc.text = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ProcessedContent
# ---------------------------------------------------------------------------


def test_processed_content_defaults() -> None:
    pc = ProcessedContent()
    assert pc.title == ""
    assert pc.summary == ""
    assert pc.key_concepts == []
    assert pc.error is None


def test_processed_content_with_error() -> None:
    pc = ProcessedContent(error="insufficient_content")
    assert pc.error == "insufficient_content"


def test_processed_content_full() -> None:
    pc = ProcessedContent(
        title="My Article",
        summary="This is a summary.",
        key_concepts=["python", "async"],
    )
    assert pc.title == "My Article"
    assert pc.key_concepts == ["python", "async"]


# ---------------------------------------------------------------------------
# ExternalItem
# ---------------------------------------------------------------------------


def _make_processed() -> ProcessedContent:
    return ProcessedContent(
        title="Test Article",
        summary="A test summary.",
        key_concepts=["testing", "python"],
    )


def test_external_item_build_sets_id_from_url() -> None:
    url = "https://example.com/article"
    item = ExternalItem.build(
        url=url,
        user_id="user1",
        processed=_make_processed(),
        source_type="article",
        embedding=[0.1, 0.2, 0.3],
    )
    assert item.id == url_hash(url)
    assert item.content_hash == url_hash(url)


def test_external_item_build_type_is_external() -> None:
    item = ExternalItem.build(
        url="https://example.com",
        user_id="user1",
        processed=_make_processed(),
        source_type="article",
        embedding=[0.0],
    )
    assert item.type == "external"


def test_external_item_build_preserves_my_note() -> None:
    item = ExternalItem.build(
        url="https://example.com",
        user_id="user1",
        processed=_make_processed(),
        source_type="article",
        embedding=[0.0],
        my_note="interesting read",
    )
    assert item.my_note == "interesting read"


def test_external_item_build_my_note_optional() -> None:
    item = ExternalItem.build(
        url="https://example.com",
        user_id="user1",
        processed=_make_processed(),
        source_type="article",
        embedding=[0.0],
    )
    assert item.my_note is None


def test_external_item_frozen() -> None:
    item = ExternalItem.build(
        url="https://example.com",
        user_id="user1",
        processed=_make_processed(),
        source_type="article",
        embedding=[0.0],
    )
    with pytest.raises(Exception):
        item.title = "changed"  # type: ignore[misc]


def test_external_item_model_dump_excludes_embedding() -> None:
    item = ExternalItem.build(
        url="https://example.com",
        user_id="user1",
        processed=_make_processed(),
        source_type="article",
        embedding=[0.1, 0.2],
    )
    dumped = item.model_dump(exclude={"embedding"})
    assert "embedding" not in dumped
    assert dumped["title"] == "Test Article"
