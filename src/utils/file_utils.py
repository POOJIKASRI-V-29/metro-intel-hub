"""Generic filesystem utilities for the KMRL platform.

Scope: path safety, file hashing, extension/size inspection, and safe
temp-file handling. Content parsing (PDF/DOCX/image extraction) belongs
in `ingestion/*_parser.py`, not here -- this module never opens a file
for anything beyond hashing or byte-count purposes.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from config.logging_config import get_logger
from utils.constants import EXTENSION_TO_MIME_TYPE, SupportedMimeType

logger = get_logger(__name__)

_DEFAULT_HASH_CHUNK_SIZE_BYTES = 65536  # 64 KB read chunks for hashing


def get_safe_filename(original_filename: str) -> str:
    """Sanitizes a user-supplied filename to prevent directory traversal.

    Strips any directory components (e.g. "../../etc/passwd" ->
    "passwd") and removes characters that are unsafe on common
    filesystems, while preserving the original extension.

    Args:
        original_filename: The filename as supplied by the upload client,
            which must never be trusted as a literal path component.

    Returns:
        A sanitized filename containing only the base name, with unsafe
        characters replaced by underscores.

    Example:
        >>> get_safe_filename("../../etc/passwd")
        'passwd'
        >>> get_safe_filename("report (final)v2.pdf")
        'report_final_v2.pdf'
    """
    base_name = Path(original_filename).name  # strips any path components
    safe_chars = []
    for char in base_name:
        if char.isalnum() or char in (".", "-", "_"):
            safe_chars.append(char)
        elif char == " ":
            continue
        else:
            safe_chars.append("_")
    sanitized = "".join(safe_chars).strip("_")
    return sanitized or "unnamed_file"


def get_file_extension(filename: str) -> str:
    """Returns the lowercase file extension (with leading dot) of a filename.

    Args:
        filename: The filename to inspect.

    Returns:
        The lowercase extension, e.g. ".pdf". Returns an empty string if
        the filename has no extension.
    """
    return Path(filename).suffix.lower()


def get_mime_type_from_extension(filename: str) -> Optional[SupportedMimeType]:
    """Looks up the canonical MIME type for a filename's extension.

    Args:
        filename: The filename to inspect.

    Returns:
        The corresponding `SupportedMimeType`, or None if the extension
        is not in `EXTENSION_TO_MIME_TYPE` (i.e. unsupported).
    """
    extension = get_file_extension(filename)
    return EXTENSION_TO_MIME_TYPE.get(extension)


def compute_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """Computes a hex digest hash of a file's contents, read in chunks.

    Used for duplicate-upload detection (comparing hashes rather than
    filenames, so a re-uploaded file with a different name is still
    recognized as identical content).

    Args:
        file_path: Path to the file on disk.
        algorithm: Hash algorithm name accepted by `hashlib.new()`
            (e.g. "sha256", "md5").

    Returns:
        The hex digest string of the file's contents.

    Raises:
        FileNotFoundError: If `file_path` does not exist.
        ValueError: If `algorithm` is not a recognized hash algorithm.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Cannot hash non-existent file: {file_path}")

    try:
        hasher = hashlib.new(algorithm)
    except ValueError as exc:
        raise ValueError(f"Unsupported hash algorithm: {algorithm!r}") from exc

    with file_path.open("rb") as file_handle:
        while chunk := file_handle.read(_DEFAULT_HASH_CHUNK_SIZE_BYTES):
            hasher.update(chunk)

    return hasher.hexdigest()


def get_file_size_bytes(file_path: Path) -> int:
    """Returns the size of a file on disk, in bytes.

    Args:
        file_path: Path to the file on disk.

    Returns:
        File size in bytes.

    Raises:
        FileNotFoundError: If `file_path` does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Cannot stat non-existent file: {file_path}")
    return file_path.stat().st_size


def ensure_directory_exists(directory: Path) -> Path:
    """Creates a directory (including parents) if it does not already exist.

    Args:
        directory: The directory path to ensure exists.

    Returns:
        The same `Path`, for convenient chaining.
    """
    directory.mkdir(parents=True, exist_ok=True)
    return directory


@contextmanager
def temporary_file_copy(source_path: Path, suffix: Optional[str] = None) -> Iterator[Path]:
    """Creates a temporary copy of a file, cleaned up automatically on exit.

    Useful when a downstream library (e.g. a specific OCR engine) requires
    exclusive access to a file path, or when a parser needs to operate on
    a copy without risking mutation of the original uploaded file.

    Args:
        source_path: Path to the original file to copy.
        suffix: Optional suffix (including dot) to force on the temp file,
            e.g. ".pdf". Defaults to the source file's own suffix.

    Yields:
        Path to the temporary copy. The file and its containing temp
        directory are removed automatically when the context exits, even
        if an exception is raised inside the block.

    Raises:
        FileNotFoundError: If `source_path` does not exist.

    Example:
        >>> with temporary_file_copy(Path("upload.pdf")) as temp_path:
        ...     process_with_external_tool(temp_path)
        # temp_path is deleted here automatically
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Cannot copy non-existent file: {source_path}")

    resolved_suffix = suffix or source_path.suffix
    temp_dir = Path(tempfile.mkdtemp(prefix="kmrl_tmp_"))
    temp_path = temp_dir / f"copy{resolved_suffix}"

    try:
        shutil.copy2(source_path, temp_path)
        yield temp_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)