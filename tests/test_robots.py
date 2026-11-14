from scraper import SteamScraper


class FakeResponse:
    status_code = 200
    text = "User-agent: *\nDisallow: /app/99/\n"
    encoding = "utf-8"

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def get(self, url, timeout):
        self.calls.append(url)
        return FakeResponse()


def test_robots_is_checked_once_and_disallowed_url_is_rejected():
    session = FakeSession()
    scraper = SteamScraper(session=session, jeda=0)
    assert scraper.boleh_diambil("https://store.steampowered.com/app/10/")
    assert not scraper.boleh_diambil("https://store.steampowered.com/app/99/")
    assert session.calls == ["https://store.steampowered.com/robots.txt"]
