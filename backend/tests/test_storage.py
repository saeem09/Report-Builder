from pathlib import Path

import pytest

from app.storage import read_file, save_file


def test_save_and_read_file_roundtrip(tmp_path: Path) -> None:
    file_id = save_file(b"hello world", "notes.txt", uploads_dir=tmp_path)

    result = read_file(file_id, "notes.txt", uploads_dir=tmp_path)

    assert result == b"hello world"


def test_save_file_returns_a_unique_id_per_call(tmp_path: Path) -> None:
    first_id = save_file(b"one", "a.txt", uploads_dir=tmp_path)
    second_id = save_file(b"two", "b.txt", uploads_dir=tmp_path)

    assert first_id != second_id


def test_save_file_blocks_path_traversal_in_original_name(tmp_path: Path) -> None:
    file_id = save_file(b"x", "../../escaped.txt", uploads_dir=tmp_path)

    escaped_path = tmp_path.parent.parent / "escaped.txt"
    assert not escaped_path.exists()

    expected_path = tmp_path / file_id / "escaped.txt"
    assert expected_path.exists()
    assert expected_path.read_bytes() == b"x"


def test_save_file_rejects_empty_sanitized_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        save_file(b"x", "", uploads_dir=tmp_path)

    with pytest.raises(ValueError):
        save_file(b"x", ".", uploads_dir=tmp_path)


def test_save_file_rejects_dot_dot_sanitized_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        save_file(b"x", "..", uploads_dir=tmp_path)

    with pytest.raises(ValueError):
        save_file(b"x", "../..", uploads_dir=tmp_path)
