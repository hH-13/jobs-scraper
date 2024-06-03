from typing import Any, Generator, Optional

from markdownify import markdownify
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from src.utils import Browser, BrowserHandler, Portal


class GetIndeed(Portal, BrowserHandler):
    """gets jobs from Indeed"""

    def __init__(self, domain: str, browser_name: Browser, **kwargs) -> None:
        """
        domain: the top-level indeed domain name, like www.indeed.com or in.indeed.com
        browser_name: the browser to be used for scraping
        """
        super().__init__(domain=domain, browser_name=browser_name, **kwargs)
        self.elems = {
            # general elements
            "anchor": dict(by=By.TAG_NAME, value="a"),
            "button": dict(by=By.CSS_SELECTOR, value="button"),
            # filters
            "filters": dict(by=By.CLASS_NAME, value="yosegi-FilterPill-dropdownPillContainer"),
            "filter_option": dict(by=By.CLASS_NAME, value="yosegi-FilterPill-dropdownListItemLink"),
            # job info related
            "job_card": dict(by=By.CLASS_NAME, value="cardOutline"),
            "job_title": dict(by=By.CLASS_NAME, value="jcs-JobTitle"),
            "job_desc": dict(by=By.CLASS_NAME, value="jobsearch-JobComponent"),
        }
        print("gi")

    def _get_jobs_url(self, **kwargs) -> Generator[str, None, None]:
        "generate page-wise url for base jobs page"
        try:
            search_term = kwargs["search_term"]
            loc = kwargs["loc"]
            rad = f'&radius={kwargs.get('search_rad', 5)}' if loc.upper() != "REMOTE" else ""
            sort_by_date = "&sort=date" if kwargs["sort_by_date"] else ""
            num_pages = 1 if not (n := kwargs.get("num_pages")) else n
        except KeyError as e:
            raise KeyError(f"Please check your search : {kwargs}") from e

        base = f"{self.domain}/jobs?q={search_term}&l={loc}{rad}{sort_by_date}"

        for n in range(num_pages):
            yield f"{base}&start={n*10}"

    def _get_available_options(self) -> dict[str, list[str]]:
        driver = self._driver
        available_options = dict()
        for options in driver.find_elements(**self.elems["filters"]):
            try:
                button = options.find_element(**self.elems["button"])
                button.click()
                available_options[button.text] = [
                    option.text for option in options.find_elements(**self.elems["filter_option"])
                ]
            except NoSuchElementException as e:
                print("Error while retrieving available options")
                print(repr(e))
                continue
        return available_options

    def search(
        self,
        search_term: str,
        loc: str,
        search_rad: Optional[int] = None,
        sort_by_date: bool = False,
        num_pages: Optional[int] = None,
        only_options: bool = False,
        **kwargs,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        print(kwargs)
        # ~open browser~ -- actually, should already be open
        driver = self._driver
        jobs: list[dict[str, Any]] = []
        available_options = dict(
            search_term=search_term, location=loc, search_radius=search_rad, num_pages=num_pages, url=[]
        )

        # navigate to indeed base url
        for page in self._get_jobs_url(
            search_term=search_term,
            loc=loc,
            search_rad=search_rad,
            sort_by_date=sort_by_date,
            num_pages=num_pages,
        ):
            self.get(page)
            print(page)
            available_options["url"].append(page)
            if page.endswith("=0"):
                # optionally collect available filters/options
                try:
                    available_options.update(self._get_available_options())  # type: ignore
                except NoSuchElementException as e:
                    available_options.update(dict(error=[repr(e)]))  # type: ignore
            if only_options:
                return available_options, jobs
            # get title, link for each job found on the page
            for job in driver.find_elements(**self.elems["job_card"]):
                j: dict[str, str | None] = {"title": None, "url": None}
                try:
                    j["title"] = job.find_element(**self.elems["job_title"]).text
                    j["url"] = job.find_element(**self.elems["anchor"]).get_attribute("href")
                except NoSuchElementException as e:
                    print(e)
                jobs.append(j)
        return available_options, jobs

    def get_job_details(self, job_url: str) -> str | None:
        """
        go to the job page and get the job description
        """
        self.get(job_url)
        try:
            return markdownify(
                self._driver.find_element(**self.elems["job_desc"]).get_attribute("innerHTML"),
                strip=["a"],
            )
        except NoSuchElementException:
            print(f"Unable to retrieve JD for {job_url}")
            return None
