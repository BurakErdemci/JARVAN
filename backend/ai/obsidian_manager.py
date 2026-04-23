from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


logger = logging.getLogger(__name__)


class ObsidianManagerError(Exception):
    """Base exception for ObsidianManager."""


class InvalidNoteTitleError(ObsidianManagerError, ValueError):
    """Raised when a note title is invalid."""


class UnsafePathError(ObsidianManagerError, ValueError):
    """Raised when a resolved path is outside the vault."""


class NoteNotFoundError(ObsidianManagerError, FileNotFoundError):
    """Raised when a note cannot be found."""


@dataclass(frozen=True)
class NoteData:
    metadata: dict[str, Any]
    content: str
    path: Path


class ObsidianManager:
    """
    Manage markdown notes in an Obsidian vault.

    Features:
    - Create notes with YAML frontmatter
    - Read and parse notes
    - Search notes by title and/or content
    - List notes in the vault

    Security:
    - Prevents path traversal
    - Sanitizes note titles and folder paths
    """

    _INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
    _FRONTMATTER_PATTERN = re.compile(
        r"^---\s*\n(.*?)\n---\s*\n?(.*)$",
        re.DOTALL,
    )

    def __init__(self, vault_path: str | Path) -> None:
        """
        Initialize the manager with a vault path.

        Parameters:
            vault_path: Path to the Obsidian vault. Created if missing.
        """
        self.vault_path = Path(vault_path).expanduser().resolve()
        self.vault_path.mkdir(parents=True, exist_ok=True)

        if not self.vault_path.is_dir():
            raise NotADirectoryError(f"Vault path is not a directory: {self.vault_path}")

        logger.debug("ObsidianManager initialized with vault: %s", self.vault_path)

    def create_note(
        self,
        title: str,
        content: str,
        folder: str | Path | None = None,
        tags: list[str] | tuple[str, ...] | None = None,
        overwrite: bool = False,
    ) -> Path:
        """
        Create a markdown note with YAML frontmatter.

        Parameters:
            title: Note title.
            content: Note body content.
            folder: Optional subfolder inside the vault.
            tags: Optional list of tags for frontmatter.
            overwrite: Whether to overwrite if the note already exists.

        Returns:
            Path to the created note.

        Raises:
            InvalidNoteTitleError: If title is invalid.
            FileExistsError: If note exists and overwrite is False.
            UnsafePathError: If resolved path escapes the vault.
        """
        note_path = self._resolve_path(title=title, folder=folder)

        if note_path.exists() and not overwrite:
            raise FileExistsError(f"Note already exists: {note_path}")

        note_path.parent.mkdir(parents=True, exist_ok=True)

        clean_tags = self._normalize_tags(tags)
        frontmatter = self._build_frontmatter(
            title=title.strip(),
            tags=clean_tags,
            created=datetime.now(timezone.utc),
        )

        body = content if content is not None else ""
        final_content = f"{frontmatter}\n# {title.strip()}\n\n{body.rstrip()}\n"

        note_path.write_text(final_content, encoding="utf-8")
        logger.info("Created note: %s", note_path)
        return note_path

    def read_note(self, title: str, folder: str | Path | None = None) -> dict[str, Any]:
        """
        Read a note and parse its metadata/content.

        Parameters:
            title: Note title.
            folder: Optional subfolder inside the vault.

        Returns:
            Dictionary with keys: metadata, content, path.

        Raises:
            NoteNotFoundError: If the note does not exist.
        """
        note_path = self._resolve_path(title=title, folder=folder)

        if not note_path.exists() or not note_path.is_file():
            raise NoteNotFoundError(f"Note not found: {note_path}")

        parsed = self._parse_note(note_path)
        logger.debug("Read note: %s", note_path)
        return {
            "metadata": parsed.metadata,
            "content": parsed.content,
            "path": str(parsed.path),
        }

    def search_notes(
        self,
        query: str,
        search_in_content: bool = True,
        case_sensitive: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Search notes by title and optionally content.

        Parameters:
            query: Search query string.
            search_in_content: Whether to search within note content.
            case_sensitive: Whether the search should be case-sensitive.

        Returns:
            List of matching notes, sorted by relative path.
            Each item contains:
            - title
            - path
            - metadata
            - match_in_title
            - match_in_content
        """
        query = (query or "").strip()
        if not query:
            return []

        results: list[dict[str, Any]] = []
        normalized_query = query if case_sensitive else query.lower()
        query_words = [w for w in normalized_query.split() if len(w) > 1]
        if not query_words:
            query_words = [normalized_query]

        for file_path in sorted(self.vault_path.rglob("*.md")):
            if not file_path.is_file():
                continue

            try:
                parsed = self._parse_note(file_path)
            except Exception as exc:
                logger.warning("Failed to parse note during search: %s (%s)", file_path, exc)
                continue

            relative_path = file_path.relative_to(self.vault_path)
            title = str(parsed.metadata.get("title") or file_path.stem)

            haystack_title = title if case_sensitive else title.lower()
            haystack_content = parsed.content if case_sensitive else parsed.content.lower()

            # En az bir kelime eşleşiyorsa sonucu dahil et
            title_match = any(word in haystack_title for word in query_words)
            content_match = search_in_content and any(word in haystack_content for word in query_words)

            if title_match or content_match:
                results.append(
                    {
                        "title": title,
                        "path": str(file_path),
                        "relative_path": str(relative_path),
                        "metadata": parsed.metadata,
                        "match_in_title": title_match,
                        "match_in_content": content_match,
                    }
                )

        results.sort(key=lambda item: str(item["relative_path"]).lower())
        logger.debug("Search query '%s' returned %d result(s)", query, len(results))
        return results

    def list_notes(self, folder: str | Path | None = None) -> list[str]:
        """
        List markdown notes in the vault or in a specific subfolder.

        Parameters:
            folder: Optional subfolder inside the vault.

        Returns:
            List of relative note paths as strings.
        """
        base_path = self._resolve_folder(folder)
        notes = [
            str(path.relative_to(self.vault_path))
            for path in sorted(base_path.rglob("*.md"))
            if path.is_file()
        ]
        logger.debug("Listed %d note(s) under %s", len(notes), base_path)
        return notes

    def _sanitize_filename(self, title: str) -> str:
        """
        Sanitize and validate a note title for filesystem safety.

        Returns:
            Safe filename stem without extension.

        Raises:
            InvalidNoteTitleError: If the title is empty or unsafe.
        """
        if not isinstance(title, str):
            raise InvalidNoteTitleError("Note title must be a string.")

        cleaned = title.strip()
        if not cleaned:
            raise InvalidNoteTitleError("Note title cannot be empty.")

        if cleaned in {".", ".."}:
            raise InvalidNoteTitleError("Note title cannot be '.' or '..'.")

        if "/" in cleaned or "\\" in cleaned:
            raise InvalidNoteTitleError("Note title cannot contain path separators.")

        if self._INVALID_FILENAME_CHARS.search(cleaned):
            raise InvalidNoteTitleError(f"Note title contains invalid characters: {title!r}")

        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            raise InvalidNoteTitleError("Note title became empty after sanitization.")

        return cleaned

    def _normalize_tags(self, tags: list[str] | tuple[str, ...] | None) -> list[str]:
        """Normalize, deduplicate, and validate tags."""
        if not tags:
            return []

        normalized: list[str] = []
        seen: set[str] = set()

        for tag in tags:
            if not isinstance(tag, str):
                continue

            clean = tag.strip().lstrip("#")
            clean = re.sub(r"\s+", "-", clean)
            if not clean:
                continue

            if clean not in seen:
                seen.add(clean)
                normalized.append(clean)

        return normalized

    def _build_frontmatter(
        self,
        title: str,
        tags: list[str] | None = None,
        created: datetime | None = None,
    ) -> str:
        """Build YAML frontmatter string."""
        payload: dict[str, Any] = {
            "title": title,
            "created": (created or datetime.now(timezone.utc)).isoformat(),
            "tags": tags or [],
        }
        yaml_text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False).strip()
        return f"---\n{yaml_text}\n---\n"

    def _resolve_folder(self, folder: str | Path | None) -> Path:
        """
        Resolve a folder safely inside the vault.

        Raises:
            UnsafePathError: If resolved folder escapes the vault.
        """
        if folder is None or str(folder).strip() == "":
            return self.vault_path

        folder_path = Path(folder)

        if folder_path.is_absolute():
            raise UnsafePathError("Absolute folder paths are not allowed.")

        candidate = (self.vault_path / folder_path).resolve()

        try:
            candidate.relative_to(self.vault_path)
        except ValueError as exc:
            raise UnsafePathError(f"Folder escapes vault: {folder}") from exc

        return candidate

    def _resolve_path(self, title: str, folder: str | Path | None = None) -> Path:
        """
        Resolve a note path safely inside the vault.

        Raises:
            InvalidNoteTitleError: If title is invalid.
            UnsafePathError: If resolved path escapes the vault.
        """
        safe_title = self._sanitize_filename(title)
        base_folder = self._resolve_folder(folder)
        note_path = (base_folder / f"{safe_title}.md").resolve()

        try:
            note_path.relative_to(self.vault_path)
        except ValueError as exc:
            raise UnsafePathError(f"Resolved note path escapes vault: {note_path}") from exc

        return note_path

    def _parse_note(self, file_path: str | Path) -> NoteData:
        """
        Parse a markdown note into metadata and content.

        If no frontmatter exists, metadata defaults to an empty dict.
        """
        path = Path(file_path).resolve()
        raw = path.read_text(encoding="utf-8")

        metadata: dict[str, Any] = {}
        content = raw

        match = self._FRONTMATTER_PATTERN.match(raw)
        if match:
            frontmatter_raw, content_raw = match.groups()
            parsed_yaml = yaml.safe_load(frontmatter_raw) or {}
            metadata = parsed_yaml if isinstance(parsed_yaml, dict) else {}
            content = content_raw

        return NoteData(metadata=metadata, content=content, path=path)