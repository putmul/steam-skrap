"""Bot Telegram SteamScrap.

Bot ini hanya membaca data dari MariaDB. Scraping tetap dijalankan oleh main.py.
Jalankan setelah BOT_TOKEN dan database dikonfigurasi:

    python steam-skrap/bot.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
from collections import Counter
from datetime import time as datetime_time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRAPER_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRAPER_ROOT))

from database.database import Database

try:
    from telegram import BotCommand, Update
    from telegram.ext import (
        Application,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )
except ImportError:  # bot.py masih dapat diimpor untuk menguji fungsi formatter
    BotCommand = Update = Application = CommandHandler = ContextTypes = None
    MessageHandler = filters = None

import config

log = logging.getLogger("steamscrap.bot")
WIB = ZoneInfo(config.TIMEZONE)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_REPORT_TIME = os.getenv("BOT_REPORT_TIME", "08:00")

BANTUAN = (
    "Perintah SteamScrap:\n"
    "/start - Sapaan dan daftar command\n"
    "/help - Menampilkan bantuan\n"
    "/ringkas - Statistik katalog game\n"
    "/terbaru - Menampilkan 10 game terbaru\n"
    "/cari <kata> - Cari berdasarkan nama, genre, atau tag\n"
    "/detail <app_id> - Detail lengkap game\n"
    "/genre <nama> - Game berdasarkan genre\n"
    "/gratis - Menampilkan 10 game gratis\n"
    "/langganan - Aktifkan laporan harian\n"
    "/berhenti - Hentikan laporan harian"
)


def _json_list(value):
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else []
    except (TypeError, json.JSONDecodeError):
        return [item.strip() for item in str(value).split(",") if item.strip()]


def _price(value):
    try:
        amount = Decimal(str(value or 0))
    except (InvalidOperation, ValueError):
        amount = Decimal("0")
    if amount == 0:
        return "Gratis"
    return f"Rp {amount:,.2f}"


def _date(value):
    return value.strftime("%d-%m-%Y") if hasattr(value, "strftime") else str(value or "-")


def _jumlah(args, default=10):
    if not args:
        return default
    try:
        jumlah = int(args[0])
    except ValueError as exc:
        raise ValueError("Jumlah harus berupa angka.") from exc
    if jumlah < 1 or jumlah > 20:
        raise ValueError("Jumlah harus antara 1 dan 20.")
    return jumlah


def _game_text(game, nomor=None):
    prefix = f"{nomor}. " if nomor is not None else ""
    genres = ", ".join(_json_list(game.get("genres"))) or "-"
    tags = ", ".join(_json_list(game.get("tags"))) or "-"
    return (
        f"{prefix}{game.get('nama') or '(tanpa nama)'}\n"
        f"Tanggal rilis: {_date(game.get('release_date'))}\n"
        f"Genre: {genres}\n"
        f"Tag: {tags}\n"
        f"Harga: {_price(game.get('harga_setelah_diskon'))}\n"
        f"Rating: {game.get('rating') or '-'}\n"
        f"Link: {game.get('link_url') or '-'}"
    )


def format_game_list(games, title="Daftar game"):
    if not games:
        return "Tidak ada game yang ditemukan."
    return title + "\n\n" + "\n\n".join(
        _game_text(game, nomor) for nomor, game in enumerate(games, 1)
    )


def format_summary(games):
    if not games:
        return "Belum ada data game. Jalankan scraper terlebih dahulu."
    all_genres = [genre for game in games for genre in _json_list(game.get("genres"))]
    genre_terbanyak = Counter(all_genres).most_common(1)
    prices = []
    for game in games:
        try:
            prices.append(Decimal(str(game.get("harga_setelah_diskon") or 0)))
        except (InvalidOperation, ValueError):
            pass
    rata_rata = sum(prices, Decimal("0")) / len(prices) if prices else Decimal("0")
    genre_text = genre_terbanyak[0][0] if genre_terbanyak else "-"
    return (
        "Ringkasan katalog Steam\n"
        f"Jumlah game: {len(games)}\n"
        f"Genre terbanyak: {genre_text}\n"
        f"Rata-rata harga: {_price(rata_rata)}"
    )


def query_db(sql, params=()):
    """Jalankan SELECT dan kembalikan list dictionary."""
    database = Database()
    cursor = None
    try:
        database.connect()
        cursor = database.connection.cursor(dictionary=True)
        cursor.execute(sql, params)
        return list(cursor.fetchall())
    finally:
        if cursor is not None:
            cursor.close()
        database.close()


def query_games(limit=10):
    return query_db(
        """
        SELECT app_id, release_date, nama, genres, tags, harga_asli,
               harga_setelah_diskon, link_url, image_url, rating, mature_content
        FROM games WHERE is_active = TRUE
        ORDER BY release_date DESC, nama ASC
        LIMIT %s
        """,
        (limit,),
    )


def query_search(keyword, limit=10):
    term = f"%{keyword.lower()}%"
    return query_db(
        """
        SELECT app_id, release_date, nama, genres, tags, harga_asli,
               harga_setelah_diskon, link_url, image_url, rating, mature_content
        FROM games
        WHERE is_active = TRUE AND (
            LOWER(nama) LIKE %s OR LOWER(genres) LIKE %s OR LOWER(tags) LIKE %s
        )
        ORDER BY release_date DESC, nama ASC
        LIMIT %s
        """,
        (term, term, term, limit),
    )


def query_detail(app_id):
    rows = query_db(
        """
        SELECT app_id, release_date, nama, genres, tags, diskon_persen,
               harga_asli, harga_setelah_diskon, link_url, image_url,
               rating, mature_content
        FROM games WHERE app_id = %s AND is_active = TRUE
        """,
        (app_id,),
    )
    return rows[0] if rows else None


def query_genre(genre, limit=10):
    return query_db(
        """
        SELECT app_id, release_date, nama, genres, tags, harga_asli,
               harga_setelah_diskon, link_url, image_url, rating, mature_content
        FROM games
        WHERE is_active = TRUE AND LOWER(genres) LIKE %s
        ORDER BY release_date DESC, nama ASC
        LIMIT %s
        """,
        (f'%"{genre.lower()}"%', limit),
    )


def query_free(limit=10):
    return query_db(
        """
        SELECT app_id, release_date, nama, genres, tags, harga_asli,
               harga_setelah_diskon, link_url, image_url, rating, mature_content
        FROM games
        WHERE is_active = TRUE AND harga_setelah_diskon = 0
        ORDER BY release_date DESC, nama ASC
        LIMIT %s
        """,
        (limit,),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nama = update.effective_user.first_name if update.effective_user else ""
    await update.message.reply_text(f"Halo, {nama}! Aku SteamScrap.\n\n{BANTUAN}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(BANTUAN)


async def ringkas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_summary(query_db(
        "SELECT nama, genres, harga_setelah_diskon FROM games WHERE is_active = TRUE"
    )))


async def terbaru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_game_list(query_games(10), "Game terbaru"))


async def cari(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Contoh: /cari survival")
        return
    keyword = " ".join(context.args)
    await update.message.reply_text(
        format_game_list(query_search(keyword), f'Hasil pencarian "{keyword}"')
    )


async def detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Contoh: /detail 570")
        return
    game = query_detail(int(context.args[0]))
    await update.message.reply_text(
        _game_text(game) if game else "Game tidak ditemukan."
    )


async def genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Contoh: /genre Action")
        return
    name = " ".join(context.args)
    await update.message.reply_text(
        format_game_list(query_genre(name), f"Game genre {name}")
    )


async def gratis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_game_list(query_free(10), "Game gratis"))


async def kirim_laporan_harian(context: ContextTypes.DEFAULT_TYPE):
    games = query_games(5)
    text = format_summary(query_db(
        "SELECT nama, genres, harga_setelah_diskon FROM games WHERE is_active = TRUE"
    ))
    text += "\n\n" + format_game_list(games, "5 game terbaru")
    await context.bot.send_message(chat_id=context.job.chat_id, text=text)


async def langganan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.job_queue is None:
        await update.message.reply_text("JobQueue belum tersedia. Install python-telegram-bot[job-queue].")
        return
    try:
        jam, menit = map(int, BOT_REPORT_TIME.split(":", 1))
        waktu = datetime_time(jam, menit, tzinfo=WIB)
    except (ValueError, TypeError):
        await update.message.reply_text("BOT_REPORT_TIME harus berformat HH:MM.")
        return
    nama_job = f"laporan-{update.effective_chat.id}"
    for job in context.job_queue.get_jobs_by_name(nama_job):
        job.schedule_removal()
    context.job_queue.run_daily(
        kirim_laporan_harian,
        time=waktu,
        chat_id=update.effective_chat.id,
        name=nama_job,
    )
    await update.message.reply_text(f"Laporan harian aktif pukul {BOT_REPORT_TIME} WIB.")


async def berhenti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nama_job = f"laporan-{update.effective_chat.id}"
    jobs = context.job_queue.get_jobs_by_name(nama_job) if context.job_queue else []
    for job in jobs:
        job.schedule_removal()
    await update.message.reply_text(
        "Laporan harian dihentikan." if jobs else "Kamu belum berlangganan."
    )


async def tidak_dikenal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Perintah tidak dikenal. Ketik /help.")


async def saat_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.error("Error saat memproses update", exc_info=context.error)
    if Update is not None and isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("Maaf, terjadi kesalahan. Coba lagi.")


async def setelah_mulai(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start", "Sapaan dan daftar command"),
        BotCommand("help", "Menampilkan bantuan"),
        BotCommand("ringkas", "Statistik katalog game"),
        BotCommand("terbaru", "Game terbaru"),
        BotCommand("cari", "Cari game"),
        BotCommand("detail", "Detail game"),
        BotCommand("genre", "Game berdasarkan genre"),
        BotCommand("gratis", "Game gratis"),
        BotCommand("langganan", "Aktifkan laporan harian"),
        BotCommand("berhenti", "Hentikan laporan harian"),
    ])


def buat_aplikasi(token):
    if Application is None:
        raise RuntimeError(
            "Dependency Telegram belum terpasang. Jalankan: "
            "pip install python-telegram-bot[job-queue]"
        )
    application = Application.builder().token(token).post_init(setelah_mulai).build()
    handlers = {
        "start": start,
        "help": help_command,
        "ringkas": ringkas,
        "terbaru": terbaru,
        "cari": cari,
        "detail": detail,
        "genre": genre,
        "gratis": gratis,
        "langganan": langganan,
        "berhenti": berhenti,
    }
    for name, function in handlers.items():
        application.add_handler(CommandHandler(name, function))
    application.add_handler(MessageHandler(filters.COMMAND, tidak_dikenal))
    application.add_error_handler(saat_error)
    return application


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN belum diisi pada file .env")
    app = buat_aplikasi(BOT_TOKEN)
    log.info("Bot SteamScrap berjalan")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
