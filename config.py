"""Konfigurasi sederhana SteamScrap."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"

SEARCH_URL = "https://store.steampowered.com/search/?sort_by=Released_DESC&page={page}"
DETAIL_URL = "https://store.steampowered.com/app/{app_id}/"
ROBOTS_URL = "https://store.steampowered.com/robots.txt"

USER_AGENT = os.getenv(
    "USER_AGENT",
    "SteamScrap/1.0 (academic scraping project; contact: local-project)",
)
JEDA_DETIK = float(os.getenv("JEDA_DETIK", "1.0"))
TIMEOUT_DETIK = int(os.getenv("TIMEOUT_DETIK", "15"))
MAKS_COBA = int(os.getenv("MAKS_COBA", "3"))

TIMEZONE = "Asia/Jakarta"

NSFW_BLACKLIST = (
    "nsfw",
    "sexual content",
    "hentai",
    "nudity",
    "adult only",
    "adult content",
    "eroge",
    "pornography",
    "explicit sexual content",
)

NON_BASE_KEYWORDS = (
    "dlc",
    "downloadable content",
    "expansion",
    "add-on",
    "addon",
    "content pack",
    "season pass",
    "bundle",
    "soundtrack",
    "artbook",
    "prologue",
    "episode",
    "tool",
    "video",
)

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "steamscrap")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
