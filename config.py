# Define your lists of job titles, locations, and keywords
from typing import List

from app.job_scrapers.scraper import SearchLocation

# Job titles will form the core of the search string used by the
# scraper in the form or '"title 1" OR "title 2"' etc etc
# these job titles will also be used to ignore jobs that are returned
# but don't partially match.
# E.G. "backend team lead" will match "python backend team lead"
# "engineering manager" will not match "product manager"
JOB_TITLES = [
    "engineering manager",
    "engineering team lead",
    "software team lead",
    "backend team lead",
    "fullstack team lead",
    "cto",
    "head of engineering",
    # "senior engineer",
    # "backend engineer",
    # "python engineer"
]

# the linkedin search is weird, I think it also checks skills listed against
# the role, so any additional search terms will also be added to the search.
# Think in terms of skills that a recruiter might add to your desired role.
# Roles will still be filtered on job titles
ADDITIONAL_SEARCH_TERMS: List[str] = [
    # "agile"
    # "scrum"
]

# this is a list of locations that the scraper will loop through
JOB_LOCATIONS: List[SearchLocation] = [
    # SearchLocation(location="Berlin", remote=False),
    SearchLocation(location="European Economic Area", remote=True)
]

# the linkedin job search does not check the body text, the analyser will use
# these keywords and if found set job.keyword_match to true.
POSITIVE_MATCH_KEYWORDS: List[str] = [
    "Python",
    "Fast API",
    "GreenTech" "DeepTech"
    # add more keywords
]

# the analyser will use these keywords and if found set job.keyword_match
# to false. Think of these as terms to help you filter out roles
NEGATIVE_MATCH_KEYWORDS = ["crypto", "web3.0"]


def linkedin_search_string():
    # Format the unique phrases with quotes and join them with ' OR '
    formatted_string = (
        "(" + " OR ".join(f'"{title}"' for title in JOB_TITLES) + ")"
    )
    return formatted_string
