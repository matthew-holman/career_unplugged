from __future__ import annotations

import re

from app.utils.locations.country_resolver import CountryResolver
from app.utils.locations.europe_filter import EuropeFilter


class LocationParser:
    @classmethod
    def pick_location_candidate(
        cls, card_text: str, location_hint: str | None
    ) -> str | None:
        if location_hint:
            cleaned_hint = cls.clean_location_hint(location_hint)
            if cls.is_location_hint_valid(cleaned_hint):
                return cleaned_hint

        candidate = cls.extract_location_candidate_from_text(card_text)
        if candidate:
            return candidate

        return None

    @classmethod
    def extract_location_candidate_from_text(cls, text: str) -> str | None:
        if not text:
            return None

        for chunk in re.split(r"[|•·/]+", text):
            if cls.is_location_hint_valid(chunk):
                return cls.clean_location_hint(chunk)

        pattern = re.compile(r"([A-Za-zÀ-ÖØ-öø-ÿ.'\- ]+),\s*([A-Za-zÀ-ÖØ-öø-ÿ.'\- ]+)")
        for match in pattern.finditer(text):
            candidate = f"{match.group(1).strip()}, {match.group(2).strip()}"
            if cls.is_location_hint_valid(candidate):
                return cls.clean_location_hint(candidate)

        return None

    @classmethod
    def is_location_hint_valid(cls, hint: str) -> bool:
        """
        "Valid" here means: it looks like a specific country or a city/location
        we can resolve to a country, OR one of a few known region tokens (e.g. Europe).
        """
        cleaned = cls.clean_location_hint(hint)
        if not cleaned:
            return False

        lowered = cleaned.lower()
        if re.search(r"\b(eu|emea|europe|european union)\b", lowered):
            return True

        # Handle comma forms by checking both sides against our two primitives:
        # - is_country(token): token is a country name
        # - resolve_country(token): token is a city/location and returns its country
        if "," in cleaned:
            left, right = (p.strip() for p in cleaned.split(",", 1))
            if (
                (right and CountryResolver.is_country(right))
                or (left and CountryResolver.resolve_country(left) is not None)
                or (right and CountryResolver.resolve_country(right) is not None)
            ):
                return True

        if CountryResolver.is_country(cleaned):
            return True

        if CountryResolver.resolve_country(cleaned) is not None:
            return True

        return False

    @classmethod
    def clean_location_hint(cls, hint: str) -> str:
        # Normalize whitespace first
        cleaned = " ".join(hint.split())

        # Remove parenthetical qualifiers: "(remote)", "(hybrid)", "(onsite)", etc.
        # This removes any (...) including surrounding whitespace
        cleaned = re.sub(r"\s*\([^)]*\)", "", cleaned)

        # Normalize separators
        cleaned = re.sub(r"[·|/]+", ", ", cleaned)
        cleaned = cleaned.replace("—", "-").replace("–", "-")

        # Trim junk punctuation
        cleaned = cleaned.strip(" ,;|-")

        # Canonical normalization (case, accents, etc.)
        cleaned = cls.normalize_location(cleaned)

        lowered = cleaned.lower()
        ignore_tokens = {"head office", "hq", "global", "multiple locations"}
        if lowered in ignore_tokens:
            return ""

        return cleaned

    @classmethod
    def parse_location(
        cls,
        location_raw: str | None,
        *,
        prefer_europe: bool = True,
    ) -> tuple[str | None, str | None]:
        """
        Parse an ATS location string into (city, country_or_region).

        Rules:
          - Remove remote/hybrid/onsite markers, but preserve commas (City, Country).
          - If multi-location (e.g. "Remote, APAC; Remote, Netherlands; ..."):
              - Prefer first European chunk (if prefer_europe=True)
              - Else pick first chunk
          - Interpret "City, Country" when possible.
          - If no resolvable city->country, treat token as country/region.
        """
        if not location_raw:
            return None, None

        normalized = cls.normalize_location(location_raw)
        if not normalized:
            return None, None

        candidates = cls._split_location_candidates(normalized)
        if not candidates:
            return None, None

        primary = cls._pick_primary_candidate(candidates, prefer_europe=prefer_europe)
        if not primary:
            return None, None

        city, country = cls._parse_single_location_candidate(primary)
        if city:
            city = CountryResolver.resolve_alias(city)
        return city, country

    @staticmethod
    def normalize_location(location: str) -> str:
        """
        Keep delimiters needed for parsing (commas/semicolons),
        remove remote/hybrid-ish markers, and normalise whitespace/punctuation.
        """
        text = " ".join(location.strip().split())

        # remove markers (do not remove commas/semicolons)
        # NOTE: order matters: handle multi-word before single-word
        patterns = [
            r"\bfully\s+remote\b",
            r"\bremote[-\s]?first\b",
            r"\bon[-\s]?site\b",
            r"\bonsite\b",
            r"\bhybrid\b",
            r"\bremote\b",
            r"\bgreater\b",
            r"\bmetropolitan\b",
            r"\barea\b",
            r"\bregion\b",
        ]
        for pattern in patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # normalise dashes and comma spacing; keep ';' as separator
        text = text.replace("—", "-").replace("–", "-")
        text = re.sub(r"\s*[-]\s*", " - ", text)
        text = re.sub(r"\s*,\s*", ", ", text)
        text = re.sub(r"\s{2,}", " ", text).strip()

        # trim leftover punctuation created by marker removals
        text = text.strip(" ,;|-")
        return text

    @staticmethod
    def _split_location_candidates(normalized: str) -> list[str]:
        """
        Split multi-location strings into candidate chunks.
        Primary separator: ';'
        """
        parts = [LocationParser._clean_part(p) for p in normalized.split(";")]
        return [p for p in parts if p]

    @staticmethod
    def _clean_part(value: str) -> str:
        # strip leading/trailing separators: space, comma, semicolon, pipe, dash
        return re.sub(r"^[\s,;|\-]+|[\s,;|\-]+$", "", value)

    @classmethod
    def _pick_primary_candidate(
        cls,
        candidates: list[str],
        *,
        prefer_europe: bool,
    ) -> str | None:
        if not candidates:
            return None

        if not prefer_europe:
            return candidates[0]

        for candidate in candidates:
            # Prefer right side of comma if present (country-ish), else whole token.
            countryish = (
                candidate.split(",", 1)[-1].strip() if "," in candidate else candidate
            )
            if EuropeFilter.is_european(countryish):
                return candidate

        return candidates[0]

    @classmethod
    def _parse_single_location_candidate(  # noqa: C901
        cls, candidate: str
    ) -> tuple[str | None, str | None]:
        """
        Parse a single candidate like:
          - "Berlin, Germany"
          - "London, United Kingdom"
          - "Netherlands"
          - "Europe"
          - "United States & Canada"
          - "London" (if resolvable as city -> country)

        Contract assumptions:
          - CountryResolver.is_country(token) == token is a country name
          - CountryResolver.resolve_country(token) returns a country string IFF token
            is a city/location
        """
        candidate = candidate.strip()
        if not candidate:
            return None, None

        if "," in candidate:
            left_raw, right_raw = (p.strip() for p in candidate.split(",", 1))
            left = cls._clean_atom(left_raw)
            right = cls._clean_atom(right_raw)

            if not left and not right:
                return None, None

            # 1) Classic "City, Country"
            if right and CountryResolver.is_country(right):
                return left, right

            # 2) Left is a city/location -> resolve to country
            if left:
                resolved_left_country = CountryResolver.resolve_country(left)
                if resolved_left_country:
                    return left, resolved_left_country

            # 3) Right is a city/location -> resolve to country (salvage odd formats)
            if right:
                resolved_right_country = CountryResolver.resolve_country(right)
                if resolved_right_country:
                    return right, resolved_right_country

            # 4) Fallback: keep the most country/region-ish side if present.
            return None, right or left

        token = cls._clean_atom(candidate)
        if not token:
            return None, None

        resolved_country = CountryResolver.resolve_country(token)
        if resolved_country:
            return token, resolved_country

        return None, token

    @staticmethod
    def _clean_atom(value: str | None) -> str | None:
        if not value:
            return None
        value = value.strip()
        if not value:
            return None
        value = re.sub(r"^[,;|\-]+|[,;|\-]+$", "", value).strip()
        return value or None
