class CountryResolver:
    CITY_TO_COUNTRY = {
        # Sweden
        "stockholm": "Sweden",
        "gothenburg": "Sweden",
        "göteborg": "Sweden",
        "malmö": "Sweden",
        "HQ(Stockholm)": "Sweden",

        # Romania
        "timisoara": "Romania",
        "iasi": "Romania",
        "sibiu": "Romania",
        "bucharest": "Romania",

        # Baltics
        "rīga": "Latvia",
        "riga": "Latvia",
        "vilnius": "Lithuania",
        "kaunas": "Lithuania",

        # Portugal
        "lisbon": "Portugal",
        "porto": "Portugal",

        # Germany
        "berlin": "Germany",

        # Netherlands
        "amsterdam": "Netherlands",

        # United Kingdom
        "london": "United Kingdom",
    }

    @classmethod
    def resolve_country(cls, city: str | None) -> str | None:
        if not city:
            return None

        key = city.strip().lower()
        return cls.CITY_TO_COUNTRY.get(key)
