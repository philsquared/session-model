from dataclasses import dataclass, field

from sessionmodel.Speaker import Speaker


@dataclass
class Session:
    id: str
    title: str
    abstract: str
    length: str | None
    audience: list[str]
    tags: list[str]
    speakers: list[Speaker]
    outline: str | None
    type: str = "session"
