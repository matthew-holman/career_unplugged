import re


class CountryResolver:
    CITY_TO_COUNTRY = {
        # Argentina
        "buenos aires": "Argentina",
        # Armenia
        "yerevan": "Armenia",
        # Australia
        "melbourne": "Australia",
        "sydney": "Australia",
        "brisbane": "Australia",
        # Austria
        "vienna": "Austria",
        # Belgium
        "brussels": "Belgium",
        # Canada
        "toronto": "Canada",
        "vancouver": "Canada",
        "montreal": "Canada",
        "waterloo": "Canada",
        "ottawa": "Canada",
        # Czechia
        "prague": "Czechia",
        # Denmark
        "copenhagen": "Denmark",
        # Estonia
        "tallinn": "Estonia",
        "tartu": "Estonia",
        # Finland
        "helsinki": "Finland",
        # France
        "paris": "France",
        "lyon": "France",
        # Germany
        "berlin": "Germany",
        "munich": "Germany",
        "münchen": "Germany",
        "hamburg": "Germany",
        # Greece
        "athens": "Greece",
        # Hungary
        "budapest": "Hungary",
        # India
        "gurgaon": "India",
        "gurugram": "India",
        "bangalore": "India",
        "bengaluru": "India",
        "hyderabad": "India",
        "pune": "India",
        "mumbai": "India",
        "new delhi": "India",
        "delhi": "India",
        # Ireland
        "dublin": "Ireland",
        # Italy
        "jesi": "Italy",
        "milan": "Italy",
        "milano": "Italy",
        "rome": "Italy",
        "roma": "Italy",
        # Latvia / Lithuania (Baltics)
        "rīga": "Latvia",
        "riga": "Latvia",
        "vilnius": "Lithuania",
        "kaunas": "Lithuania",
        # Netherlands
        "amsterdam": "Netherlands",
        "haarlem": "Netherlands",
        "rotterdam": "Netherlands",
        "utrecht": "Netherlands",
        # Norway
        "tøyen": "Norway",
        "oslo": "Norway",
        # Poland
        "warsaw": "Poland",
        "krakow": "Poland",
        "kraków": "Poland",
        "wroclaw": "Poland",
        "wrocław": "Poland",
        # Portugal
        "lisbon": "Portugal",
        "porto": "Portugal",
        # Romania
        "timisoara": "Romania",
        "timișoara": "Romania",
        "iasi": "Romania",
        "iași": "Romania",
        "sibiu": "Romania",
        "bucharest": "Romania",
        "bucharesti": "Romania",
        # Serbia
        "beograd": "Serbia",
        "belgrade": "Serbia",
        # Singapore
        "singapore": "Singapore",
        # South Africa
        "cape town": "South Africa",
        "capetown": "South Africa",
        "johannesburg": "South Africa",
        # Spain
        "barcelona": "Spain",
        "madrid": "Spain",
        # Sweden
        "alingsås": "Sweden",
        "gothenburg": "Sweden",
        "göteborg": "Sweden",
        "kolbäck": "Sweden",
        "linköping": "Sweden",
        "lund": "Sweden",
        "malmö": "Sweden",
        "partille": "Sweden",
        "stockholm": "Sweden",
        "sundsvall": "Sweden",
        "umeå": "Sweden",
        "uppsala": "Sweden",
        "västerås": "Sweden",
        # Switzerland
        "zurich": "Switzerland",
        "zürich": "Switzerland",
        "geneva": "Switzerland",
        # United Kingdom
        "brighton": "United Kingdom",
        "cardiff": "United Kingdom",
        "london": "United Kingdom",
        "manchester": "United Kingdom",
        "edinburgh": "United Kingdom",
        "cambridge": "United Kingdom",
        # United States (cities + a few state abbrev aliases you’ll see in listings)
        "san francisco": "United States",
        "south san francisco": "United States",
        "palo alto": "United States",
        "redwood city": "United States",
        "mountain view": "United States",
        "san mateo": "United States",
        "oakland": "United States",
        "los angeles": "United States",
        "seattle": "United States",
        "new york": "United States",
        "denver": "United States",
        "washington": "United States",
        "washington dc": "United States",
        "d.c": "United States",
        "dc": "United States",
        "austin": "United States",
        "boston": "United States",
        "chicago": "United States",
        "atlanta": "United States",
        "miami": "United States",
        # Ambiguous listing shorthand (optional; helps “NY or SF” token fallback)
        "ny": "United States",
        "sf": "United States",
        "usa": "United States",
        "u.s": "United States",
        "us": "United States",
        # Note: "frisco" is ambiguous (US city + nickname for SF). If you want it to map to US anyway:
        "frisco": "United States",
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
