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
    "Engineering Lead",
    "software team lead",
    "backend team lead",
    "fullstack team lead",
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
]

# the linkedin search is weird, I think it also checks skills listed against
# the role, so any additional search terms will also be added to the search.
# Think in terms of skills that a recruiter might add to your desired role.
# Roles will still be filtered on job titles
ADDITIONAL_SEARCH_TERMS: List[str] = ["Agile", "scrum"]

# jobs from these companies will be ignored
# Crossover seems a company to avoid
COMPANIES_TO_IGNORE: List[str] = ["Canonical", "Crossover"]

# this is a list of locations that the scraper will loop through
# remote false will search for roles listed as onsite and hybrid,
# remote true will search for remote
JOB_LOCATIONS: List[SearchLocation] = [
    SearchLocation(location="Berlin, Germany", remote=False),
    SearchLocation(location="Berlin, Germany", remote=True),
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
    SearchLocation(location="European Union", remote=True),
    SearchLocation(location="Finland", remote=True),
    SearchLocation(location="Helsinki Metropolitan Area", remote=True),
    SearchLocation(location="EMEA", remote=True),
]

# the linkedin job search does not check the body text, the analyser will use
# these keywords and if found set job.keyword_match to true.
POSITIVE_MATCH_KEYWORDS: List[str] = [
    "Python",
    "Typescript",
    "NestJs",
    "FastAPI",
    "GreenTech",
    "DeepTech",
    "Vue",
    "sustainability",
    "Node",
    "energy",
    # add more keywords
]

# the analyser will use these keywords and if found set job.keyword_match
# to false. Think of these as terms to help you filter out roles
NEGATIVE_MATCH_KEYWORDS = [
    "crypto",
    "web3",
    "blockchain",
    "Java",
    "C#",
    "Kotlin",
]


def linkedin_search_string():
    # Format the unique phrases with quotes and join them with ' OR '
    search_terms = JOB_TITLES + ADDITIONAL_SEARCH_TERMS
    formatted_string = "(" + " OR ".join(f'"{string}"' for string in search_terms) + ")"
    return formatted_string
