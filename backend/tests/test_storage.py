from pathlib import Path

from app.storage import read_file, save_file


def test_save_and_read_file_roundtrip(tmp_path: Path) -> None:
    file_id = save_file(b"hello world", "notes.txt", uploads_dir=tmp_path)

    result = read_file(file_id, "notes.txt", uploads_dir=tmp_path)

    assert result == b"hello world"


def test_save_file_returns_a_unique_id_per_call(tmp_path: Path) -> None:
    first_id = save_file(b"one", "a.txt", uploads_dir=tmp_path)
    second_id = save_file(b"two", "b.txt", uploads_dir=tmp_path)

    assert first_id != second_id
