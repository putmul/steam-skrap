"""Entry point pipeline SteamScrap."""
import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# File ini berada di steam-skrap/, sedangkan database/ berada satu level di atas.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRAPER_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRAPER_ROOT))

import config
from database.database import Database
from scraper import SteamScraper

config.LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_DIR / "steam_scraper.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("steamscrap")


def tanggal_target():
    sekarang = datetime.now(ZoneInfo(config.TIMEZONE)).date()
    return sekarang - timedelta(days=1)


def jalankan_pipeline(target_date=None, limit=None):
    target_date = target_date or tanggal_target()
    database = Database()
    scraper = SteamScraper()
    try:
        # robots.txt diperiksa sebelum koneksi/database dan sebelum halaman Steam.
        scraper.check_robots_txt()
        database.connect()
        database.ensure_schema()
        games, blocked = scraper.collect_games(
            target_date, limit=limit, is_blocked=database.is_blocked
        )
        for item in blocked:
            database.save_blocked_app(item["app_id"], item["alasan"])
        for game in games:
            database.upsert_game(game)
        database.commit()
        log.info(
            "Scraping %s selesai: %d game disimpan, %d diblokir, %d request",
            target_date, len(games), len(blocked), scraper.jumlah_request,
        )
        return games
    except Exception:
        database.rollback()
        log.exception("Pipeline gagal")
        return []
    finally:
        database.close()


def jalankan_scheduler():
    """Scheduler ringan yang memakai waktu Asia/Jakarta."""
    sudah_jalan = None
    log.info("Scheduler aktif; scraping setiap hari pukul 02:00 Asia/Jakarta")
    while True:
        sekarang = datetime.now(ZoneInfo(config.TIMEZONE))
        if sekarang.hour == 2 and sekarang.minute == 0 and sudah_jalan != sekarang.date():
            jalankan_pipeline()
            sudah_jalan = sekarang.date()
        time.sleep(20)


def main():
    parser = argparse.ArgumentParser(description="Scraper game baru Steam")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--test-scrape", action="store_true", help="ambil maksimal 5 game H-1")
    mode.add_argument("--once", action="store_true", help="ambil semua game valid H-1")
    mode.add_argument("--schedule", action="store_true", help="jalan setiap hari pukul 02:00 WIB")
    args = parser.parse_args()

    if args.schedule:
        jalankan_scheduler()
    elif args.once:
        jalankan_pipeline(limit=None)
    else:
        jalankan_pipeline(limit=5)


if __name__ == "__main__":
    main()
