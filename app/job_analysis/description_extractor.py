from __future__ import annotations

from typing import Protocol

from bs4 import BeautifulSoup

from app.models.job import Source


class DescriptionExtractor(Protocol):
    source: Source

    @staticmethod
    def extract_description(soup: BeautifulSoup) -> str: ...  # noqa: E704


class DescriptionExtractorFactory:
    _extractors: list[type[DescriptionExtractor]] = []

    @classmethod
    def register(cls, extractor_cls: type[DescriptionExtractor]) -> None:
        cls._extractors.append(extractor_cls)

    @classmethod
    def get_for_source(cls, source: Source) -> DescriptionExtractor | None:
        for extractor_cls in cls._extractors:
            if extractor_cls.source == source:
                return extractor_cls()
        return None
