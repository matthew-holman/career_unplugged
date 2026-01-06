import re

from typing import Optional


class EuropeFilter:
    """
    Conservative Europe matcher.
    If a location does not clearly match Europe, it should be rejected.
    """

    # ISO-style country names (common English forms)
    EUROPEAN_COUNTRIES = {
        # EU
        "austria",
        "belgium",
        "bulgaria",
        "croatia",
        "cyprus",
        "czech republic",
        "czechia",
        "denmark",
        "estonia",
        "finland",
        "france",
        "germany",
        "greece",
        "hungary",
        "ireland",
        "italy",
        "latvia",
        "lithuania",
        "luxembourg",
        "malta",
        "netherlands",
        "poland",
        "portugal",
        "romania",
        "slovakia",
        "slovenia",
        "spain",
        "sweden",
        # Non-EU Europe
        "united kingdom",
        "uk",
        "norway",
        "switzerland",
        "iceland",
        "serbia",
        "bosnia",
        "bosnia and herzegovina",
        "montenegro",
        "albania",
        "north macedonia",
        "moldova",
        "ukraine",
        "belarus",
        "georgia",
        "armenia",
        "azerbaijan",
    }

    # Regional / pan-European markers
    EUROPEAN_REGIONS = {
        "europe",
        "eu",
        "e.u.",
        "emea",
        "european union",
        "european economic area",
        "eea",
        "europe timezone",
        "european timezones",
        "cet",
        "cest",
        "gmt",
    }

    @classmethod
    def is_european(cls, country_or_region: Optional[str]) -> bool:
        if not country_or_region:
            return False

        value = country_or_region.strip().lower()

        # Exact matches first
        if value in cls.EUROPEAN_COUNTRIES:
            return True

        if value in cls.EUROPEAN_REGIONS:
            return True

        # Token-based fallback
        tokens = re.split(r"[,\-/()\s]+", value)
        for token in tokens:
            if token in cls.EUROPEAN_COUNTRIES:
                return True
            if token in cls.EUROPEAN_REGIONS:
                return True

        return False
