import re


class CountryResolver:
    CITY_TO_COUNTRY = {
        # Argentina
        "buenos aires": "Argentina",
        # Armenia
        "yerevan": "Armenia",
        # Australia
        "melbourne": "Australia",
        # Baltics
        "rīga": "Latvia",
        "riga": "Latvia",
        "vilnius": "Lithuania",
        "kaunas": "Lithuania",
        # Estonia
        "tallinn": "Estonia",
        "tartu": "Estonia",
        # France
        "paris": "France",
        # Germany
        "berlin": "Germany",
        # India
        "gurugram": "India",
        # Netherlands
        "amsterdam": "Netherlands",
        "Haarlem": "Netherlands",
        # Norway
        "tøyen": "Norway",
        "oslo": "Norway",
        # Romania
        "timisoara": "Romania",
        "iasi": "Romania",
        "sibiu": "Romania",
        "bucharest": "Romania",
        # Serbia
        "beograd": "serbia",
        # Spain
        "barcelona": "Spain",
        "madrid": "Spain",
        # Sweden
        "stockholm": "Sweden",
        "gothenburg": "Sweden",
        "göteborg": "Sweden",
        "malmö": "Sweden",
        "uppsala": "Sweden",
        # Poland
        "warsaw": "Poland",
        # Portugal
        "lisbon": "Portugal",
        "porto": "Portugal",
        # United Kingdom
        "london": "United Kingdom",
    }

    @classmethod
    def resolve_country(cls, location: str | None) -> str | None:
        if not location:
            return None

        normalized = location.strip().lower()

        # 1. Exact match
        if normalized in cls.CITY_TO_COUNTRY:
            return cls.CITY_TO_COUNTRY[normalized]

        # 2. Token-based fallback
        for part in normalized.split():
            cleaned = re.sub(r"[^a-zåäö]", "", part)
            if not cleaned:
                continue

            country = cls.CITY_TO_COUNTRY.get(cleaned)
            if country:
                return country

        return None
