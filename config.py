"""Konfigurasi sederhana SteamScrap."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

ROOT = PROJECT_ROOT
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


def _env_float(name, default):
    try:
        value = float(os.getenv(name, str(default)))
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


def _env_int(name, default):
    try:
        value = int(os.getenv(name, str(default)))
        return value if value >= 0 else default
    except (TypeError, ValueError):
        return default

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
    "artbook"
)

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "steamscrap")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_REPORT_TIME = os.getenv("BOT_REPORT_TIME", "08:00")
BOT_CONNECT_TIMEOUT = _env_float("BOT_CONNECT_TIMEOUT", 30)
BOT_READ_TIMEOUT = _env_float("BOT_READ_TIMEOUT", 30)
BOT_WRITE_TIMEOUT = _env_float("BOT_WRITE_TIMEOUT", 30)
BOT_POOL_TIMEOUT = _env_float("BOT_POOL_TIMEOUT", 10)
BOT_BOOTSTRAP_RETRIES = _env_int("BOT_BOOTSTRAP_RETRIES", 5)
BOT_POLL_TIMEOUT = _env_int("BOT_POLL_TIMEOUT", 10)
BOT_PROXY = os.getenv("BOT_PROXY", "").strip() or None
