"""Pengambilan dan parsing halaman Steam."""
import logging
import random
import re
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from urllib import robotparser
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

import config

log = logging.getLogger(__name__)


def parse_steam_date(text):
    """Parse tanggal lengkap Steam; teks seperti TBA/2026 menghasilkan None."""
    value = " ".join((text or "").replace("\xa0", " ").split())
    for pattern in ("%d %b, %Y", "%b %d, %Y", "%d %b %Y", "%b %d %Y"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            pass
    return None


def parse_idr_price(text):
    """Parse harga Rupiah menjadi Decimal. Harga gratis menjadi 0.00."""
    value = (text or "").strip().lower()
    if not value or "free" in value or "gratis" in value:
        return Decimal("0.00") if value else None

    value = value.replace("idr", "").replace("rp", "").replace(" ", "")
    match = re.search(r"[\d.,]+", value)
    if not match:
        return None
    number = match.group()
    if "," in number and "." in number:
        if number.rfind(",") > number.rfind("."):
            number = number.replace(".", "").replace(",", ".")
        else:
            number = number.replace(",", "")
    elif "," in number:
        after = number.rsplit(",", 1)[1]
        number = number.replace(",", "." if len(after) == 2 else "")
    elif "." in number:
        after = number.rsplit(".", 1)[1]
        if len(after) != 2:
            number = number.replace(".", "")
    try:
        return Decimal(number).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _text(node):
    return node.get_text(" ", strip=True) if node else ""


def _unique(values):
    result = []
    seen = set()
    for value in values:
        value = " ".join(value.split())
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _app_id_from_url(url):
    match = re.search(r"/app/(\d+)", url or "")
    return int(match.group(1)) if match else None


def parse_search_page(html, page_url=""):
    """Ambil kandidat game dari satu halaman hasil pencarian Steam."""
    soup = BeautifulSoup(html or "", "html.parser")
    result = []
    for row in soup.select("a.search_result_row"):
        href = urljoin(page_url, row.get("href", ""))
        app_id = row.get("data-ds-appid") or _app_id_from_url(href)
        if not app_id:
            continue
        try:
            app_id = int(str(app_id).split(",")[0])
        except ValueError:
            continue
        name = _text(row.select_one(".search_name")) or _text(row.select_one(".title"))
        release_text = _text(row.select_one(".search_released"))
        result.append({
            "app_id": app_id,
            "nama": name,
            "release_date": parse_steam_date(release_text),
            "release_text": release_text,
            "url": href or config.DETAIL_URL.format(app_id=app_id),
        })
    return result


def parse_app_detail(html, app_id=None, url=""):
    """Ambil data game dari halaman detail Steam."""
    soup = BeautifulSoup(html or "", "html.parser")
    app_id = app_id or _app_id_from_url(url)
    release_text = _text(soup.select_one(".release_date .date"))
    if not release_text:
        release_text = _text(soup.select_one(".date"))

    genres = []
    for node in soup.select(
        '#genresAndManufacturer a[href*="/genre/"], .details_block a[href*="/genre/"]'
    ):
        genres.append(_text(node))

    tags = [
        _text(node).lstrip("+").strip()
        for node in soup.select(".glance_tags .app_tag, .popular_tags .app_tag, a.app_tag")
    ]
    tags = [tag for tag in tags if tag]

    original_text = _text(soup.select_one(".discount_original_price"))
    final_text = _text(soup.select_one(".discount_final_price"))
    if not original_text:
        original_text = _text(soup.select_one(".game_purchase_price"))
    if not final_text:
        final_text = _text(soup.select_one(".game_purchase_price"))
    discount_text = _text(soup.select_one(".discount_pct"))
    discount_match = re.search(r"\d+", discount_text)

    mature = _text(soup.select_one(".mature_content, #mature_content"))
    description = _text(
        soup.select_one(".game_description_snippet, #game_area_description")
    )
    content_type = _text(soup.select_one("#app_type, .app_type, .game_area_details_specs"))
    image = soup.select_one("img.game_header_image_full, img.game_header_image")
    rating = _text(soup.select_one(".user_reviews_summary_row .game_review_summary"))
    detail_url = url or config.DETAIL_URL.format(app_id=app_id)

    return {
        "app_id": int(app_id) if app_id is not None else None,
        "nama": _text(soup.select_one(".apphub_AppName, #appHubAppName")),
        "release_date": parse_steam_date(release_text),
        "genres": _unique(genres),
        "tags": _unique(tags),
        "diskon_persen": int(discount_match.group()) if discount_match else 0,
        "harga_asli": parse_idr_price(original_text) or Decimal("0.00"),
        "harga_setelah_diskon": parse_idr_price(final_text) or Decimal("0.00"),
        "link_url": detail_url,
        "image_url": image.get("src", "") if image else "",
        "rating": rating,
        "mature_content": mature,
        "description": description,
        "content_type": content_type,
    }


def is_base_game(game):
    """Return False untuk DLC/added content dan produk non-game."""
    text = " ".join(
        str(game.get(key, "")) for key in ("nama", "description", "content_type")
    ).lower()
    if "this content requires the base application" in text:
        return False
    if any(keyword in text for keyword in config.NON_BASE_KEYWORDS):
        return False
    return True


def nsfw_reason(game):
    fields = (
        ("tags", game.get("tags", [])),
        ("genres", game.get("genres", [])),
        ("mature content", game.get("mature_content", "")),
    )
    for field, value in fields:
        text = str(value).lower()
        for keyword in config.NSFW_BLACKLIST:
            if keyword in text:
                return f"{field}: {keyword}"
    return None


def is_nsfw(game):
    return nsfw_reason(game) is not None


class SteamScraper:
    """Scraper kecil dengan pemeriksaan robots.txt sekali per proses."""

    def __init__(self, session=None, jeda=config.JEDA_DETIK):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})
        self.jeda = jeda
        self.robots = None
        self.jumlah_request = 0
        self.gagal = []

    def check_robots_txt(self):
        """Ambil dan parse robots.txt. Gagal membaca berarti stop (fail closed)."""
        if self.robots is not None:
            return self.robots
        try:
            response = self.session.get(config.ROBOTS_URL, timeout=config.TIMEOUT_DETIK)
            self.jumlah_request += 1
            response.raise_for_status()
            parser = robotparser.RobotFileParser()
            parser.set_url(config.ROBOTS_URL)
            parser.parse(response.text.splitlines())
            self.robots = parser
            log.info("robots.txt berhasil diperiksa")
            return parser
        except (RequestException, OSError, ValueError) as exc:
            log.error("Tidak dapat memeriksa robots.txt: %s", exc)
            raise RuntimeError("robots.txt tidak dapat diperiksa") from exc

    def boleh_diambil(self, url):
        return self.check_robots_txt().can_fetch(config.USER_AGENT, url)

    def get_html(self, url):
        """GET halaman yang diizinkan robots.txt, dengan retry sederhana."""
        if not self.boleh_diambil(url):
            raise PermissionError(f"robots.txt melarang URL: {url}")
        for attempt in range(1, config.MAKS_COBA + 1):
            try:
                if self.jeda:
                    time.sleep(self.jeda)
                response = self.session.get(url, timeout=config.TIMEOUT_DETIK)
                self.jumlah_request += 1
                if response.status_code == 429:
                    raise RequestException("429 Too Many Requests")
                response.raise_for_status()
                response.encoding = "utf-8"
                return response.text
            except RequestException as exc:
                if attempt == config.MAKS_COBA:
                    break
                wait = 2 ** attempt + random.random()
                log.warning("Gagal mengambil %s (percobaan %d): %s", url, attempt, exc)
                time.sleep(wait)
        log.error("Menyerah mengambil %s", url)
        self.gagal.append(url)
        return None

    def find_release_candidates(self, target_date, max_pages=None):
        """Yield kandidat dari search yang diurutkan berdasarkan tanggal rilis terbaru."""
        self.check_robots_txt()
        page = 1
        while max_pages is None or page <= max_pages:
            url = config.SEARCH_URL.format(page=page)
            html = self.get_html(url)
            if html is None:
                break
            candidates = parse_search_page(html, url)
            if not candidates:
                break
            stop = False
            for candidate in candidates:
                release_date = candidate["release_date"]
                if release_date is None:
                    continue
                if release_date > target_date:
                    continue
                if release_date < target_date:
                    stop = True
                    break
                yield candidate
            if stop:
                break
            page += 1

    def scrape_app_detail(self, candidate):
        app_id = candidate["app_id"]
        url = candidate.get("url") or config.DETAIL_URL.format(app_id=app_id)
        html = self.get_html(url)
        if html is None:
            return None
        return parse_app_detail(html, app_id=app_id, url=url)

    def collect_games(self, target_date, limit=None, is_blocked=None):
        """Ambil game valid dan kembalikan (games, blocked_apps)."""
        games = []
        blocked = []
        for candidate in self.find_release_candidates(target_date):
            app_id = candidate["app_id"]
            if is_blocked and is_blocked(app_id):
                log.info("App %s sudah diblokir; dilewati", app_id)
                continue
            try:
                game = self.scrape_app_detail(candidate)
            except (PermissionError, RuntimeError):
                raise
            except Exception as exc:
                log.warning("Detail app %s gagal diproses: %s", app_id, exc)
                continue
            if not game or game.get("release_date") != target_date:
                continue
            if not is_base_game(game):
                log.info("App %s bukan base game; dilewati", app_id)
                continue
            reason = nsfw_reason(game)
            if reason:
                blocked.append({"app_id": app_id, "alasan": reason})
                continue
            games.append(game)
            if limit and len(games) >= limit:
                break
        return games, blocked


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(parse_steam_date("14 Nov, 2026"))
