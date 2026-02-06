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
        "wien": "Austria",
        "vienna": "Austria",
        # Belgium
        "brussels": "Belgium",
        # Bosnia
        "bosnia": "Bosnia",
        "sarajevo": "Bosnia",
        "banja luka": "Bosnia",
        "tuzla": "Bosnia",
        "zenica": "Bosnia",
        "mostar": "Bosnia",
        # Brazil
        "sao paulo": "Brazil",
        "são paulo": "Brazil",
        "rio de janeiro": "Brazil",
        "brasilia": "Brazil",
        "brasília": "Brazil",
        "salvador": "Brazil",
        "fortaleza": "Brazil",
        # Bulgaria
        "sofia": "Bulgaria",
        "plovdiv": "Bulgaria",
        "varna": "Bulgaria",
        "burgas": "Bulgaria",
        "ruse": "Bulgaria",
        # Canada
        "toronto": "Canada",
        "vancouver": "Canada",
        "montreal": "Canada",
        "waterloo": "Canada",
        "ottawa": "Canada",
        # China
        "hong kong": "China",
        "shanghai": "China",
        # Croatia
        "zagreb": "Croatia",
        "split": "Croatia",
        "rijeka": "Croatia",
        "osijek": "Croatia",
        "zadar": "Croatia",
        # Cyprus
        "nicosia": "Cyprus",
        "limassol": "Cyprus",
        "larnaca": "Cyprus",
        "paphos": "Cyprus",
        # Czech Republic
        "brno": "Czech Republic",
        "prague": "Czech Republic",
        "ostrava": "Czech Republic",
        "plzen": "Czech Republic",
        "plzeň": "Czech Republic",
        "liberec": "Czech Republic",
        "olomouc": "Czech Republic",
        # Denmark
        "copenhagen": "Denmark",
        "københavn": "Denmark",
        # Estonia
        "tallinn": "Estonia",
        "tartu": "Estonia",
        "narva": "Estonia",
        "pärnu": "Estonia",
        # Finland
        "helsinki": "Finland",
        # France
        "paris": "France",
        "nantes": "France",
        "lyon": "France",
        # Georgia
        "tbilisi": "Georgia",
        "batumi": "Georgia",
        "kutaisi": "Georgia",
        "rustavi": "Georgia",
        "gori": "Georgia",
        # Germany
        "berlin": "Germany",
        "munich": "Germany",
        "münchen": "Germany",
        "hamburg": "Germany",
        "wolfsburg": "Germany",
        # Ghana
        "accra": "Ghana",
        # Greece
        "athens": "Greece",
        # Hungary
        "budapest": "Hungary",
        "debrecen": "Hungary",
        "szeged": "Hungary",
        "miskolc": "Hungary",
        "pécs": "Hungary",
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
        # Israel
        "jerusalem": "Israel",
        "tel aviv": "Israel",
        "tel-aviv": "Israel",
        "haifa": "Israel",
        "rishon lezion": "Israel",
        "petah tikva": "Israel",
        # Italy
        "jesi": "Italy",
        "milan": "Italy",
        "milano": "Italy",
        "rome": "Italy",
        "roma": "Italy",
        "venice": "Italy",
        # Japan
        "tokyo": "Japan",
        # Kenya
        "nairobi": "Kenya",
        # Kazakhstan
        "almaty": "Kazakhstan",
        "astana": "Kazakhstan",
        "nur-sultan": "Kazakhstan",
        "shymkent": "Kazakhstan",
        "karaganda": "Kazakhstan",
        "aktobe": "Kazakhstan",
        # Latvia
        "rīga": "Latvia",
        "riga": "Latvia",
        "daugavpils": "Latvia",
        "liepaja": "Latvia",
        "liepāja": "Latvia",
        # Lithuania
        "vilnius": "Lithuania",
        "kaunas": "Lithuania",
        "klaipeda": "Lithuania",
        "klaipėda": "Lithuania",
        "siauliai": "Lithuania",
        "šiauliai": "Lithuania",
        "panevezys": "Lithuania",
        "panevėžys": "Lithuania",
        # Malta
        "valletta": "Malta",
        "birkirkara": "Malta",
        "sliema": "Malta",
        "qormi": "Malta",
        "mosta": "Malta",
        # Moldova
        "moldova": "Moldova",
        "chisinau": "Moldova",
        "chișinău": "Moldova",
        "balti": "Moldova",
        "bălți": "Moldova",
        "tiraspol": "Moldova",
        "bender": "Moldova",
        "ribnita": "Moldova",
        "rîbnița": "Moldova",
        # Montenegro
        "podgorica": "Montenegro",
        "niksic": "Montenegro",
        "nikšić": "Montenegro",
        "herceg novi": "Montenegro",
        "bar": "Montenegro",
        "budva": "Montenegro",
        # Mexico
        "mexico city": "Mexico",
        # Morocco
        "casablanca": "Morocco",
        # Netherlands
        "amsterdam": "Netherlands",
        "brabant": "Netherlands",
        "eindhoven": "Netherlands",
        "haarlem": "Netherlands",
        "rotterdam": "Netherlands",
        "utrecht": "Netherlands",
        # New Zealand
        "auckland": "New Zealand",
        # North Macedonia
        "skopje": "North Macedonia",
        "bitola": "North Macedonia",
        "kumanovo": "North Macedonia",
        "prilep": "North Macedonia",
        "tetovo": "North Macedonia",
        # Norway
        "alta": "Norway",
        "bardufoss": "Norway",
        "drammen": "Norway",
        "fosen": "Norway",
        "kongsberg": "Norway",
        "tøyen": "Norway",
        "oslo": "Norway",
        "sandane": "Norway",
        "sigerfjord": "Norway",
        "steinkjer": "Norway",
        "trondheim": "Norway",
        # Philippines
        "cebu": "Philippines",
        # Poland
        "krakow": "Poland",
        "kraków": "Poland",
        "warsaw": "Poland",
        "warszawa": "Poland",
        "wroclaw": "Poland",
        "wrocław": "Poland",
        "lodz": "Poland",
        "łódź": "Poland",
        "poznan": "Poland",
        "poznań": "Poland",
        "gdansk": "Poland",
        "gdańsk": "Poland",
        "szczecin": "Poland",
        "lublin": "Poland",
        # Portugal
        "lisbon": "Portugal",
        "porto": "Portugal",
        # Romania
        "brasov": "Romania",
        "bucharest": "Romania",
        "bucharesti": "Romania",
        "cluj - Napoca": "Romania",
        "iasi": "Romania",
        "iași": "Romania",
        "oradea": "Romania",
        "sibiu": "Romania",
        "timisoara": "Romania",
        "timișoara": "Romania",
        # Serbia
        "beograd": "Serbia",
        "belgrade": "Serbia",
        "novi sad": "Serbia",
        "nis": "Serbia",
        "niš": "Serbia",
        "kragujevac": "Serbia",
        # Singapore
        "singapore": "Singapore",
        # Slovakia
        "bratislava": "Slovakia",
        "kosice": "Slovakia",
        "košice": "Slovakia",
        "presov": "Slovakia",
        "prešov": "Slovakia",
        "zilina": "Slovakia",
        "žilina": "Slovakia",
        "nitra": "Slovakia",
        # Slovenia
        "ljubljana": "Slovenia",
        "maribor": "Slovenia",
        "celje": "Slovenia",
        "kranj": "Slovenia",
        # South Africa
        "cape town": "South Africa",
        "capetown": "South Africa",
        "johannesburg": "South Africa",
        "durban": "South Africa",
        "pretoria": "South Africa",
        "gqeberha": "South Africa",
        "port elizabeth": "South Africa",
        "western cape": "South Africa",
        # Spain
        "barcelona": "Spain",
        "madrid": "Spain",
        "zaragoza": "Spain",
        "valencia": "Spain",
        "seville": "Spain",
        "sevilla": "Spain",
        "bilbao": "Spain",
        "malaga": "Spain",
        "málaga": "Spain",
        # Sweden
        "arlanda": "Sweden",
        "alingsås": "Sweden",
        "borlänge": "Sweden",
        "bromma": "Sweden",
        "fridhemsplan": "Sweden",
        "gärdet": "Sweden",
        "gävle": "Sweden",
        "gårdsten": "Sweden",
        "gothenburg": "Sweden",
        "göteborg": "Sweden",
        "halmstad": "Sweden",
        "helsingborg": "Sweden",
        "jönköping": "Sweden",
        "kalmar": "Sweden",
        "karlskoga": "Sweden",
        "karlstad": "Sweden",
        "kolbäck": "Sweden",
        "kristianstad": "Sweden",
        "kungsängen": "Sweden",
        "linköping": "Sweden",
        "lund": "Sweden",
        "malmö": "Sweden",
        "mora": "Sweden",
        "olofström": "Sweden",
        "östersund": "Sweden",
        "örebro": "Sweden",
        "partille": "Sweden",
        "piteå": "Sweden",
        "rovaniemi": "Sweden",
        "söderköping": "Sweden",
        "slöinge": "Sweden",
        "stockholm": "Sweden",
        "sundsvall": "Sweden",
        "umeå": "Sweden",
        "uppsala": "Sweden",
        "växjö": "Sweden",
        "vasastan": "Sweden",
        "västerås": "Sweden",
        "västervik": "Sweden",
        # Switzerland
        "zurich": "Switzerland",
        "zürich": "Switzerland",
        "geneva": "Switzerland",
        # Turkey
        "istanbul": "Turkey",
        "ankara": "Turkey",
        "izmir": "Turkey",
        "bursa": "Turkey",
        "antalya": "Turkey",
        # Ukraine
        "kyiv": "Ukraine",
        "kiev": "Ukraine",
        "kharkiv": "Ukraine",
        "odesa": "Ukraine",
        "odessa": "Ukraine",
        "dnipro": "Ukraine",
        "lviv": "Ukraine",
        # United Kingdom
        "aberdeen": "United Kingdom",
        "birmingham": "United Kingdom",
        "brighton": "United Kingdom",
        "bristol": "United Kingdom",
        "cambridge": "United Kingdom",
        "cardiff": "United Kingdom",
        "coventry": "United Kingdom",
        "edinburgh": "United Kingdom",
        "glasgow": "United Kingdom",
        "leeds": "United Kingdom",
        "london": "United Kingdom",
        "manchester": "United Kingdom",
        "newcastle upon tyne": "United Kingdom",
        "sheffield": "United Kingdom",
        "richmond upon thames": "United Kingdom",
        "uk": "United Kingdom",
        # United States (cities + a few state abbrev aliases you’ll see in listings)
        "ann arbor": "United States",
        "atlanta": "United States",
        "austin": "United States",
        "boston": "United States",
        "california": "United States",
        "chicago": "United States",
        "d.c": "United States",
        "dc": "United States",
        "denver": "United States",
        "devens": "United States",
        # Note: "frisco" is ambiguous (US city + nickname for SF). If you want it to map to US anyway:
        "frisco": "United States",
        "san francisco": "United States",
        "san diego": "United States",
        "south san francisco": "United States",
        "palo alto": "United States",
        "redwood city": "United States",
        "mountain view": "United States",
        "san mateo": "United States",
        "oakland": "United States",
        "los angeles": "United States",
        "seattle": "United States",
        "new york": "United States",
        "new york city": "United States",
        "washington": "United States",
        "washington dc": "United States",
        "miami": "United States",
        "menlo park": "United States",
        "omaha": "United States",
        "foster city": "United States",
        # Ambiguous listing shorthand (optional; helps “NY or SF” token fallback)
        "ca": "United States",
        "mi": "United States",
        "ny": "United States",
        "ne": "United States",
        "sf": "United States",
        "usa": "United States",
        "u.s": "United States",
        "us": "United States",
        # Regions
        "latam": "LATAM",  # Latin America
        "na": "NA",  # North America
        "namer": "NAMER",  # North America
        "apac": "APAC",  # Asia and the Pacific Region
        "emea": "EMEA",  # Europe, the Middle East, and Africa
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

    @classmethod
    def is_country(cls, location: str | None) -> bool:
        if not location:
            return False

        normalized = location.strip().lower()
        if not normalized:
            return False

        countries = {country.lower() for country in cls.CITY_TO_COUNTRY.values()}
        return normalized in countries
