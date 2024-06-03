import argparse

import duckdb
import polars as pl

from src.indeed_scraper import GetIndeed

DB_PATH = "jobs_test.db"
DDL = "definitions.sql"


def url(domain: str):
    domain = domain.lower()
    if "indeed" not in domain:
        raise ValueError(f"Invalid url `{domain}`. Only Indeed job portal is supported as of now.")
    if domain == "indeed.com":
        return "www.indeed.com"
    if len(domain.split(".")) == 3:
        return domain
    raise TypeError(f"Invalid url `{domain}`. Should be a valid top level domain of Indeed.")


parser = argparse.ArgumentParser(
    description="Scrape a job portal for job listings. Currently only supports Indeed."
)
parser.add_argument(
    "top_level_domain",
    type=url,
    nargs="?",
    default="in.indeed.com",
    help="The regional indeed website to search, e.g. `www.indeed.com` for the USA or `in.indeed.com` for India",
)
parser.add_argument(
    "-k", "--keywords", type=str, help='Your search keywords, like "Software Engineer"', required=True
)
parser.add_argument(
    "-l", "--location", type=str, help='Your search location, like "New York"', required=True
)
parser.add_argument(
    "-r",
    "--radius",
    type=int,
    help="The search radius, in mi or km, depending on the location. Ignored if location is Remote.",
)
parser.add_argument(
    "--sort_by_date",
    action="store_true",
    help="Sort the results by date. Default sorting method is by relevance",
)
parser.add_argument(
    "-n", "--num_pages", type=int, default=3, help="The number of pages of search results to return"
)

args = parser.parse_args()
# print(args)

# scrape jobs from website
with GetIndeed(domain=args.top_level_domain, browser_name="chrome") as gi:
    # get available search options and jobs
    available_options, jobs_found = gi.search(
        search_term=args.keywords,
        loc=args.location,
        search_rad=args.radius,
        sort_by_date=args.sort_by_date,
        num_pages=args.num_pages,
        # optional=4,
    )

    # add job descriptions to the jobs found
    jobs_found = [dict(job, description=gi.get_job_details(job["url"])) for job in jobs_found]

# save data to db
with duckdb.connect(DB_PATH) as con:
    # setup the database
    with open(DDL, "r") as f:
        ddl = f.read()
    con.sql(ddl)

    # adjust the scraped info and save to database
    options = pl.DataFrame([available_options]).drop("location")
    options.columns = [x.upper().replace(" ", "_") for x in options.columns]  # normalise column names

    # insert into searches, keeping track of the search_id
    lastrowid = con.sql(
        "INSERT INTO SEARCHES (SEARCH_TERM, URL, LOCATION, REMOTE, JOB_TYPE, PAY, COMPANY, JOB_LANGUAGE) SELECT SEARCH_TERM, URL, LOCATION, REMOTE, JOB_TYPE, PAY, COMPANY, JOB_LANGUAGE, FROM options RETURNING SEARCH_ID;"
    ).fetchall()[0][0]

    jobs = (
        pl.DataFrame(jobs_found)
        .drop_nulls()
        .with_columns(
            pl.col("description").str.slice(0, pl.col("description").str.find("\n=====")).alias("title"),
            pl.lit(lastrowid).alias("search_id"),  # search_id as retreived from last insert
        )
    )

    con.sql(
        "INSERT INTO JOBS (SEARCH_ID, TITLE, URL, DESCRIPTION) SELECT SEARCH_ID, TITLE, URL, DESCRIPTION FROM jobs"
    )
