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
        # France
        "paris": "France",
        "paris | headquarters": "France",
        # Germany
        "berlin": "Germany",
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
        # Sweden
        "stockholm": "Sweden",
        "gothenburg": "Sweden",
        "göteborg": "Sweden",
        "malmö": "Sweden",
        "hq (stockholm)": "Sweden",  # epidemic sound, should make a partial search
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
    def resolve_country(cls, city: str | None) -> str | None:
        if not city:
            return None

        key = city.strip().lower()
        return cls.CITY_TO_COUNTRY.get(key)
