from dataclasses import dataclass

from Speaker import Speaker


@dataclass
class Session:
    id: str
    title: str
    abstract: str
    outline: str
    length: str
    audience: [str]
    tags: [str]
    speakers: [Speaker]
