from datetime import date
from decimal import Decimal

from scraper import (
    is_base_game,
    is_nsfw,
    parse_app_detail,
    parse_idr_price,
    parse_search_page,
    parse_steam_date,
)


def test_parse_date_only_accepts_complete_date():
    assert parse_steam_date("14 Nov, 2026") == date(2026, 11, 14)
    assert parse_steam_date("Coming Soon") is None
    assert parse_steam_date("2026") is None


def test_parse_idr_price():
    assert parse_idr_price("Rp 59.999") == Decimal("59999.00")
    assert parse_idr_price("Rp 59.999,00") == Decimal("59999.00")
    assert parse_idr_price("Free to Play") == Decimal("0.00")


def test_parse_search_page():
    html = '''
    <a class="search_result_row" data-ds-appid="10" href="/app/10/Test/">
      <div class="search_name"><span class="title">Test Game</span></div>
      <div class="search_released">14 Nov, 2026</div>
    </a>
    '''
    result = parse_search_page(html, "https://store.steampowered.com/search/?page=1")
    assert result[0]["app_id"] == 10
    assert result[0]["release_date"] == date(2026, 11, 14)


def test_parse_detail_separates_genres_and_tags():
    html = '''
    <div class="apphub_AppName">Test Game</div>
    <div class="release_date"><div class="date">14 Nov, 2026</div></div>
    <div id="genresAndManufacturer"><a href="/genre/Action/">Action</a></div>
    <div class="glance_tags"><a class="app_tag">+Singleplayer</a></div>
    <div class="game_purchase_price">Rp 10.000</div>
    '''
    game = parse_app_detail(html, app_id=10, url="https://store.steampowered.com/app/10/")
    assert game["genres"] == ["Action"]
    assert game["tags"] == ["Singleplayer"]
    assert game["harga_asli"] == Decimal("10000.00")


def test_filters_added_content_and_nsfw():
    assert not is_base_game({"nama": "Example DLC", "description": ""})
    assert is_base_game({"nama": "Example Game", "description": ""})
    assert is_nsfw({"tags": ["Hentai"], "genres": [], "mature_content": ""})
