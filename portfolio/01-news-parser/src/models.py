"""Dataclass-модели для задач парсинга и результатов."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ParseTask:
    url: str
    site_key: str
    retry_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, payload: str | bytes) -> "ParseTask":
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        return cls(**json.loads(payload))


@dataclass
class Article:
    url: str
    site_key: str
    title: str
    text: str
    author: Optional[str] = None
    published_at: Optional[str] = None
    parsed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    def is_valid(self) -> bool:
        return bool(self.title and self.text and len(self.text) >= 100)


@dataclass
class ParseError:
    url: str
    site_key: str
    error: str
    status: Optional[int] = None
    occurred_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)
