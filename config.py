# Define your lists of job titles, locations, and keywords
JOB_TITLES = [
    "engineering manager",
    "engineering team lead",
    "software team lead",
    "backend team lead",
    "fullstack team lead",
    "cto",
    "head of engineering",
]

JOB_LOCATIONS = ["European Economic Area"]

KEYWORDS = [
    "Python",
    "Fast API"
    # add more keywords
]


def linkedin_search_string():
    # Format the unique phrases with quotes and join them with ' OR '
    formatted_string = (
        "(" + " OR ".join(f'"{title}"' for title in JOB_TITLES) + ")"
    )
    return formatted_string
