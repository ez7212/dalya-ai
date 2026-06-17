from __future__ import annotations

from pathlib import Path


DEFAULT_DICTIONARY_PATH = Path(__file__).resolve().parents[3] / "transcription" / "dictionary.yaml"


class TranscriptionDictionary:
    def __init__(self, sections: dict[str, list[str]]):
        self.sections = sections

    @property
    def terms(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for values in self.sections.values():
            for term in values:
                normalized = term.strip()
                key = normalized.casefold()
                if normalized and key not in seen:
                    seen.add(key)
                    result.append(normalized)
        return result

    def provider_vocabulary(self, limit: int = 1000) -> list[str]:
        return self.terms[:limit]

    def as_prompt_context(self) -> str:
        lines: list[str] = []
        for section, values in self.sections.items():
            if values:
                lines.append(f"{section}: {', '.join(values)}")
        return "\n".join(lines)


def load_transcription_dictionary(path: Path | str = DEFAULT_DICTIONARY_PATH) -> TranscriptionDictionary:
    dictionary_path = Path(path)
    sections: dict[str, list[str]] = {}
    current_section: str | None = None

    for raw_line in dictionary_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith(":") and not line.startswith("-"):
            current_section = line[:-1].strip()
            sections.setdefault(current_section, [])
            continue
        if line.startswith("-") and current_section:
            value = line[1:].strip().strip("'\"")
            if value:
                sections[current_section].append(value)

    return TranscriptionDictionary(sections)
