import uuid
from pathlib import Path

UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "uploads"


def save_file(content: bytes, original_name: str, uploads_dir: Path = UPLOADS_DIR) -> str:
    file_id = str(uuid.uuid4())
    file_dir = uploads_dir / file_id
    file_dir.mkdir(parents=True, exist_ok=True)
    (file_dir / original_name).write_bytes(content)
    return file_id


def read_file(file_id: str, original_name: str, uploads_dir: Path = UPLOADS_DIR) -> bytes:
    return (uploads_dir / file_id / original_name).read_bytes()
