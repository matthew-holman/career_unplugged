# Define your lists of job titles, locations, and keywords
from typing import List

from app.job_scrapers.scraper import SearchLocation

"""
Default job search profile.

These values represent default search behavior and filtering rules.
They are not deployment settings and may become user-configurable in the future.
"""


# Job titles will form the core of the search string used by the
# scraper in the form or '"title 1" OR "title 2"' etc etc
# these job titles will also be used to ignore jobs that are returned
# but don't partially match.
# E.G. "backend team lead" will match "python backend team lead"
# "engineering manager" will not match "product manager"
JOB_TITLES: List[str] = [
    "engineering manager",
    "senior engineering manager",
    "group engineering manager",
    "engineering director",
    "director of engineering",
    "director, engineering",
    "head of software engineering",
    "director of software engineering",
    "technical lead manager",
    "tech lead manager",
    "engineering lead manager",
    "principal engineering manager",
    "engineering team lead",
    "engineer team lead",
    "engineering lead",
    "software team lead",
    "backend team lead",
    "fullstack team lead",
    "team lead",
    "squad lead",
    "group lead",
    "tribe lead",
    "Chief Technology Officer",
    " cto ",
    "(cto)",
    "chief technical officer",
    "interim cto",
    "fractional cto",
    "head of engineering",
    "vp of engineering",
    "Software Development Manager",
    "head of technology",
    "Developer Team Lead",
    "Agile",
    "Scrum",
    "Engineering Squad Lead",
    # "Product Engineer",
    # "Technical Project Manager",
    # "Technical Product Manager",
    # "Python",
    # "FastAPI",
]

# the linkedin search is weird, I think it also checks skills listed against
# the role, so any additional search terms will also be added to the search.
# Think in terms of skills that a recruiter might add to your desired role.
# Roles will still be filtered on job titles
ADDITIONAL_SEARCH_TERMS: List[str] = ["Agile", "scrum"]

# jobs from these companies will be ignored
# Crossover seems a company to avoid
COMPANIES_TO_IGNORE: List[str] = ["Canonical", "Crossover"]

# Jobs from these locations are saved regardless of title match.
# Useful for finding local jobs with unusual titles.
PREFERRED_LOCATIONS: set[str] = {
    "Alingsås",
    "Göteborg",
    "Gothenburg",
    "Lerum",
    "Partille",
    "Malmö",
}

# this is a list of locations that the scraper will loop through
# remote false will search for roles listed as onsite and hybrid,
# remote true will search for remote
JOB_LOCATIONS: List[SearchLocation] = [
    SearchLocation(location="Berlin, Germany", remote=False),
    SearchLocation(location="Berlin, Germany", remote=True),
    SearchLocation(location="Germany", remote=True),
    SearchLocation(location="London Area, United Kingdom", remote=False),
    SearchLocation(location="London Area, United Kingdom", remote=True),
    SearchLocation(location="Amsterdam, North Holland, Netherlands", remote=False),
    SearchLocation(location="Amsterdam, North Holland, Netherlands", remote=True),
    SearchLocation(location="Sweden", remote=False),
    SearchLocation(location="Gothenburg, Västra Götaland County, Sweden", remote=False),
    SearchLocation(location="Gothenburg, Västra Götaland County, Sweden", remote=True),
    SearchLocation(location="Malmo, Skåne County, Sweden", remote=False),
    SearchLocation(location="Malmo, Skåne County, Sweden", remote=True),
    SearchLocation(location="Stockholm, Stockholm County, Sweden", remote=False),
    SearchLocation(location="Stockholm, Stockholm County, Sweden", remote=True),
    SearchLocation(location="Sweden", remote=True),
    SearchLocation(location="Denmark", remote=True),
    SearchLocation(location="Norway", remote=True),
    SearchLocation(location="Norway", remote=True),
    SearchLocation(location="European Union", remote=True),
    SearchLocation(location="Finland", remote=True),
    SearchLocation(location="Helsinki Metropolitan Area", remote=True),
    SearchLocation(location="EMEA", remote=True),
]

# Tags are extracted during analysis from the job title + description.
# Keys are the canonical display name (stored as tag.name in the DB).
# Values are regex patterns matched case-insensitively.
# Add new entries here to extend tagging without changing any other code.
TECH_STACK_TAGS: dict[str, str] = {
    # Languages
    "Python": r"\bPython\b",
    "TypeScript": r"\bTypeScript\b",
    "JavaScript": r"\bJavaScript\b",
    "Rust": r"\bRust\b",
    "Go": r"\b(Go(lang)?)\b",
    "Java": r"\bJava\b",
    "Kotlin": r"\bKotlin\b",
    "Scala": r"\bScala\b",
    "Ruby": r"\bRuby\b",
    "PHP": r"\bPHP\b",
    "C#": r"\bC#\b",
    "C++": r"\bC\+\+\b",
    "Elixir": r"\bElixir\b",
    "Swift": r"\bSwift\b",
    # Backend frameworks
    "FastAPI": r"\bFastAPI\b",
    "Django": r"\bDjango\b",
    "Flask": r"\bFlask\b",
    "Spring": r"\bSpring\b",
    "Node.js": r"\bNode\.?js\b",
    "NestJS": r"\bNestJS\b",
    "Express.js": r"\bExpress\.?js\b",
    "Rails": r"\b(Ruby\s+on\s+)?Rails\b",
    "Laravel": r"\bLaravel\b",
    "Phoenix": r"\bPhoenix\b",
    "Axum": r"\bAxum\b",
    "Actix": r"\bActix\b",
    # Frontend frameworks
    "React": r"\bReact\b",
    "Next.js": r"\bNext\.js\b",
    "Vue.js": r"\bVue\.?js\b",
    "Angular": r"\bAngular\b",
    "Svelte": r"\bSvelte\b",
    # Databases — relational
    "PostgreSQL": r"\b(PostgreSQL|Postgres)\b",
    "MySQL": r"\bMySQL\b",
    "SQLite": r"\bSQLite\b",
    "SQL Server": r"\bSQL\s+Server\b",
    # Databases — NoSQL
    "MongoDB": r"\bMongoDB\b",
    "Redis": r"\bRedis\b",
    "Elasticsearch": r"\b(Elasticsearch|OpenSearch)\b",
    "Cassandra": r"\bCassandra\b",
    "DynamoDB": r"\bDynamoDB\b",
    # Messaging & event streaming
    "Kafka": r"\bKafka\b",
    "RabbitMQ": r"\bRabbitMQ\b",
    "Celery": r"\bCelery\b",
    "SQS": r"\bSQS\b",
    "Pub/Sub": r"\bPub[\s/]?Sub\b",
    # Infrastructure & cloud
    "Docker": r"\bDocker\b",
    "Kubernetes": r"\b(Kubernetes|K8s)\b",
    "Terraform": r"\bTerraform\b",
    "AWS": r"\bAWS\b",
    "GCP": r"\b(GCP|Google Cloud)\b",
    "Azure": r"\bAzure\b",
    # Data & ML
    "GraphQL": r"\bGraphQL\b",
    "gRPC": r"\bgRPC\b",
    "Spark": r"\b(Apache\s+)?Spark\b",
    "Airflow": r"\b(Apache\s+)?Airflow\b",
    "dbt": r"\bdbt\b",
}

ROLE_TYPE_TAGS: dict[str, str] = {
    "Engineering Manager": r"\bengineering\s+manager\b",
    "Head of Engineering": r"\bhead\s+of\s+(software\s+)?engineering\b",
    "VP Engineering": r"\bvp\s+of\s+engineering\b",
    "Director of Engineering": r"\bdirector\s+of\s+(software\s+)?engineering\b",
    "CTO": r"\b(cto|chief\s+technology\s+officer|chief\s+technical\s+officer)\b",
    "Staff Engineer": r"\bstaff\s+(software\s+)?engineer\b",
    "Principal Engineer": r"\bprincipal\s+(software\s+)?engineer\b",
    "Tech Lead": r"\b(tech(nical)?\s+lead|team\s+lead)\b",
    "IC": r"\bindividual\s+contributor\b",
    "People Management": r"\b(line\s+manag|performance\s+review|1.on.1|one.on.one|career\s+development)\b",
    "GreenTech": r"\b(green\s*tech|cleantech|clean\s+tech|climate\s+tech|climatetech)\b",
    "DeepTech": r"\bdeep\s*tech\b",
    "Sustainability": r"\bsustainab(le|ility)\b",
    "Energy": r"\b(renewable\s+energy|clean\s+energy|energy\s+transition|energy\s+sector)\b",
}


def linkedin_search_string():
    # Format the unique phrases with quotes and join them with ' OR '
    search_terms = JOB_TITLES + ADDITIONAL_SEARCH_TERMS
    formatted_string = "(" + " OR ".join(f'"{string}"' for string in search_terms) + ")"
    return formatted_string
