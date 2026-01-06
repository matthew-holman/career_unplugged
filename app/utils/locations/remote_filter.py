from typing import Optional


class RemoteFilter:
    REMOTE_TOKENS = {
        "remote",
        "fully remote",
        "100% remote",
        "work from anywhere",
        "anywhere",
        "global",
        "worldwide",
    }

    @classmethod
    def is_remote(cls, country_or_region: Optional[str]) -> bool:
        if not country_or_region:
            return False

        value = country_or_region.strip().lower()

        # Exact or substring match
        return any(token in value for token in cls.REMOTE_TOKENS)
