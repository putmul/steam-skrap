"""Dashboard Streamlit SteamScrap.

Jalankan dari root proyek:
    streamlit run app.py
"""
import json
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SCRAPER_ROOT = PROJECT_ROOT / "steam-skrap"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRAPER_ROOT))

from database.database import Database


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


def _decimal(value):
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, ValueError):
        return Decimal("0")


@st.cache_data(ttl=300)
def load_games():
    """Ambil data game aktif dari MariaDB selama maksimal lima menit."""
    database = Database()
    cursor = None
    try:
        database.connect()
        cursor = database.connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT app_id, release_date, nama, genres, tags, diskon_persen,
                   harga_asli, harga_setelah_diskon, link_url, image_url,
                   rating, mature_content, pertama_dilihat, terakhir_dilihat
            FROM games
            WHERE is_active = TRUE
            ORDER BY release_date DESC, nama ASC
            """
        )
        return list(cursor.fetchall())
    finally:
        if cursor is not None:
            cursor.close()
        database.close()


def prepare_games(games):
    """Normalisasi data database menjadi baris yang siap ditampilkan."""
    rows = []
    for game in games:
        final_price = _decimal(game.get("harga_setelah_diskon"))
        original_price = _decimal(game.get("harga_asli"))
        rows.append({
            "app_id": game.get("app_id"),
            "nama": game.get("nama") or "(tanpa nama)",
            "release_date": game.get("release_date"),
            "genres": ", ".join(_json_list(game.get("genres"))) or "-",
            "tags": ", ".join(_json_list(game.get("tags"))) or "-",
            "diskon_persen": int(game.get("diskon_persen") or 0),
            "harga_asli": original_price,
            "harga_setelah_diskon": final_price,
            "rating": game.get("rating") or "-",
            "link_url": game.get("link_url") or "",
        })
    return rows


def genre_statistics(games):
    counts = Counter()
    prices = {}
    for game in games:
        final_price = _decimal(game.get("harga_setelah_diskon"))
        for genre in _json_list(game.get("genres")):
            counts[genre] += 1
            prices.setdefault(genre, []).append(final_price)

    rows = []
    for genre, jumlah in counts.most_common():
        values = prices.get(genre, [])
        rata_rata = sum(values, Decimal("0")) / len(values) if values else Decimal("0")
        rows.append({
            "genre": genre,
            "jumlah_game": jumlah,
            "rata_rata_harga": float(rata_rata),
        })
    return rows


def _format_rupiah(value):
    return f"Rp {float(_decimal(value)):,.2f}"


def game_table(games, sort_by, ascending=False):
    if not games:
        st.info("Tidak ada game pada kategori ini.")
        return
    frame = pd.DataFrame(games).sort_values(
        by=sort_by,
        ascending=ascending,
        na_position="last",
    )
    frame["harga_asli"] = frame["harga_asli"].map(_format_rupiah)
    frame["harga_setelah_diskon"] = frame["harga_setelah_diskon"].map(_format_rupiah)
    frame = frame[[
        "nama", "release_date", "genres", "diskon_persen",
        "harga_asli", "harga_setelah_diskon", "rating", "link_url",
    ]]
    frame.columns = [
        "Nama", "Tanggal Rilis", "Genre", "Diskon (%)",
        "Harga Asli", "Harga Setelah Diskon", "Rating", "Link Steam",
    ]
    st.dataframe(
        frame,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Link Steam": st.column_config.LinkColumn("Link Steam"),
        },
    )


st.set_page_config(page_title="SteamScrap Dashboard", page_icon="🎮", layout="wide")
st.title("🎮 SteamScrap Dashboard")
st.caption("Ringkasan katalog game Steam dari database MariaDB")

if st.sidebar.button("Refresh Data"):
    load_games.clear()
    st.rerun()

try:
    raw_games = load_games()
except Exception as exc:
    st.error("Tidak dapat membaca database MariaDB.")
    st.code(str(exc))
    st.stop()

games = prepare_games(raw_games)
if not games:
    st.warning("Database belum memiliki game aktif. Jalankan scraper terlebih dahulu.")
    st.stop()

all_genres = sorted({
    genre
    for game in raw_games
    for genre in _json_list(game.get("genres"))
})
selected_genres = st.sidebar.multiselect("Filter genre", all_genres)
search = st.sidebar.text_input("Cari nama game").strip().lower()

filtered_games = games
if selected_genres:
    filtered_games = [
        game for game in filtered_games
        if any(genre.lower() in selected_genres for genre in game["genres"].split(", "))
    ]
if search:
    filtered_games = [game for game in filtered_games if search in game["nama"].lower()]

if not filtered_games:
    st.warning("Tidak ada game yang cocok dengan filter.")
    st.stop()

paid_games = [game for game in filtered_games if game["harga_setelah_diskon"] > 0]
discounted_games = [game for game in paid_games if game["diskon_persen"] > 0]
free_games = [game for game in filtered_games if game["harga_setelah_diskon"] == 0]

prices = [game["harga_setelah_diskon"] for game in filtered_games]
average_price = sum(prices, Decimal("0")) / len(prices)
total_discounted = sum(game["diskon_persen"] > 0 for game in filtered_games)

metric_columns = st.columns(5)
metric_columns[0].metric("Jumlah Game", len(filtered_games))
metric_columns[1].metric("Game Berbayar", len(paid_games))
metric_columns[2].metric("Game Diskon", total_discounted)
metric_columns[3].metric("Free to Play", len(free_games))
metric_columns[4].metric("Rata-rata Harga", _format_rupiah(average_price))

st.subheader("Statistik per Kategori / Genre")
stats = genre_statistics(
    [raw for raw in raw_games if raw.get("app_id") in {game["app_id"] for game in filtered_games}]
)
stats_frame = pd.DataFrame(stats)
if not stats_frame.empty:
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.caption("Jumlah game per genre")
        st.bar_chart(stats_frame.head(15).set_index("genre")["jumlah_game"])
    with chart_right:
        st.caption("Rata-rata harga per genre")
        st.bar_chart(stats_frame.head(15).set_index("genre")["rata_rata_harga"])

st.subheader("Daftar Game")
tab_paid, tab_discount, tab_free = st.tabs([
    "Game Berbayar",
    "Game Diskon",
    "Free to Play",
])

with tab_paid:
    game_table(paid_games, "harga_setelah_diskon", ascending=False)

with tab_discount:
    game_table(discounted_games, "diskon_persen", ascending=False)

with tab_free:
    game_table(free_games, "release_date", ascending=False)
