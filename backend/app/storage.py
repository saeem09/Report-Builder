import uuid
from pathlib import Path

UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "uploads"


def _sanitize_name(original_name: str) -> str:
    """Strip any directory components from a user-supplied filename.

    Prevents path traversal (e.g. "../../escaped.txt") by keeping only the
    final path segment. Rejects names that sanitize down to nothing.
    """
    sanitized = Path(original_name).name
    if sanitized == "" or sanitized == ".":
        raise ValueError(f"Invalid file name: {original_name!r}")
    return sanitized


def save_file(content: bytes, original_name: str, uploads_dir: Path = UPLOADS_DIR) -> str:
    safe_name = _sanitize_name(original_name)
    file_id = str(uuid.uuid4())
    file_dir = uploads_dir / file_id
    file_dir.mkdir(parents=True, exist_ok=True)
    (file_dir / safe_name).write_bytes(content)
    return file_id


def read_file(file_id: str, original_name: str, uploads_dir: Path = UPLOADS_DIR) -> bytes:
    safe_name = _sanitize_name(original_name)
    return (uploads_dir / file_id / safe_name).read_bytes()
