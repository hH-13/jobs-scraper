from typing import Literal, Self

from selenium import webdriver

Browser = Literal["firedragon", "chrome", "firefox"]


class Portal:
    """represents a generic portal, contains methods/info that we need about the portals"""

    def __init__(self, domain: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.domain = domain if domain.startswith("http") else f"https://{domain}"
        self.domain = self.domain[:-1] if self.domain.endswith("/") else self.domain
        print("prtl")

    def _get_jobs_url(self, **kwargs) -> str:
        return self.domain


class BrowserHandler:
    """does the scraping"""

    def __init__(self, browser_name: Browser, **kwargs) -> None:
        self.browser = browser_name
        self.history = []
        print("bh")

    def __enter__(self) -> Self:
        print("ent")
        self._open_browser()
        # return self._driver
        return self

    def _open_browser(self, headless: bool = False) -> webdriver.Chrome | webdriver.Firefox:
        if self.browser == "chrome":
            from selenium.webdriver.chrome.options import Options
            # from selenium.webdriver.chrome.service import Service as ChromeService

            options = Options()
            options.add_argument("--headless=new") if headless else None
            options.add_argument("window-size=1920,1080")
            self._driver = webdriver.Chrome(
                options=options,
                # service=ChromeService(),
            )
        elif self.browser == "firefox":
            from selenium.webdriver.firefox.options import Options

            options = Options()
            options.add_argument("--headless") if headless else None
            self._driver = webdriver.Firefox(options=options)
        # elif self.browser == "firedragon":
        #     pass

        return self._driver

    def get(self, url: str) -> None:
        self.history.append(url)
        self._driver.get(url)

    def __exit__(self, *args, **kwargs) -> None:
        self._driver.quit()


class DBMan:
    pass
