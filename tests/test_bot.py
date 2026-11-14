from decimal import Decimal

from bot import _jumlah, _json_list, _price, format_game_list, format_summary


def test_bot_helpers():
    assert _jumlah([]) == 10
    assert _jumlah(["5"]) == 5
    assert _json_list('["Action", "RPG"]') == ["Action", "RPG"]
    assert _price(Decimal("0")) == "Gratis"


def test_bot_formatters():
    games = [{
        "app_id": 10,
        "nama": "Test Game",
        "release_date": "2026-11-14",
        "genres": '["Action"]',
        "tags": '["Singleplayer"]',
        "harga_setelah_diskon": "10000.00",
        "rating": "Very Positive",
        "link_url": "https://store.steampowered.com/app/10/",
    }]
    assert "Jumlah game: 1" in format_summary(games)
    assert "Test Game" in format_game_list(games)
