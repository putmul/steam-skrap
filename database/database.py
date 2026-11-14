"""Penyimpanan MariaDB untuk game Steam."""
from contextlib import contextmanager
from datetime import datetime
import json

try:
    import mysql.connector as mysql_connector
except ImportError:  # dependency diberi pesan jelas saat connect dipanggil
    mysql_connector = None

import config


class Database:
    def __init__(self, connection=None):
        self.connection = connection

    def connect(self):
        if self.connection is not None:
            return self.connection
        if mysql_connector is None:
            raise RuntimeError("Paket mysql.connector belum terpasang")
        self.connection = mysql_connector.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset="utf8mb4",
            autocommit=False,
        )
        return self.connection

    def ensure_schema(self):
        with self.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS games (
                    app_id BIGINT PRIMARY KEY,
                    release_date DATE NOT NULL,
                    nama VARCHAR(255) NOT NULL,
                    genres TEXT,
                    tags TEXT,
                    diskon_persen SMALLINT DEFAULT 0,
                    harga_asli DECIMAL(12,2) DEFAULT 0.00,
                    harga_setelah_diskon DECIMAL(12,2) DEFAULT 0.00,
                    link_url VARCHAR(500),
                    image_url VARCHAR(500),
                    rating VARCHAR(100),
                    mature_content TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    pertama_dilihat DATETIME NOT NULL,
                    terakhir_dilihat DATETIME NOT NULL
                ) CHARACTER SET utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS blocked_apps (
                    app_id BIGINT PRIMARY KEY,
                    alasan TEXT NOT NULL,
                    blocked_at DATETIME NOT NULL
                ) CHARACTER SET utf8mb4
                """
            )
        self.connection.commit()

    @contextmanager
    def cursor(self):
        cursor = self.connect().cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def is_blocked(self, app_id):
        with self.cursor() as cursor:
            cursor.execute("SELECT 1 FROM blocked_apps WHERE app_id = %s", (app_id,))
            return cursor.fetchone() is not None

    def save_blocked_app(self, app_id, reason):
        with self.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO blocked_apps (app_id, alasan, blocked_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE alasan = VALUES(alasan), blocked_at = VALUES(blocked_at)
                """,
                (app_id, reason, datetime.now()),
            )

    def upsert_game(self, game):
        now = datetime.now()
        with self.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO games (
                    app_id, release_date, nama, genres, tags, diskon_persen,
                    harga_asli, harga_setelah_diskon, link_url, image_url,
                    rating, mature_content, is_active, pertama_dilihat, terakhir_dilihat
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s, %s)
                ON DUPLICATE KEY UPDATE
                    release_date = VALUES(release_date), nama = VALUES(nama),
                    genres = VALUES(genres), tags = VALUES(tags),
                    diskon_persen = VALUES(diskon_persen), harga_asli = VALUES(harga_asli),
                    harga_setelah_diskon = VALUES(harga_setelah_diskon),
                    link_url = VALUES(link_url), image_url = VALUES(image_url),
                    rating = VALUES(rating), mature_content = VALUES(mature_content),
                    is_active = TRUE, terakhir_dilihat = VALUES(terakhir_dilihat)
                """,
                (
                    game["app_id"], game["release_date"], game.get("nama", ""),
                    json.dumps(game.get("genres", []), ensure_ascii=False),
                    json.dumps(game.get("tags", []), ensure_ascii=False),
                    game.get("diskon_persen", 0), game.get("harga_asli", 0),
                    game.get("harga_setelah_diskon", 0), game.get("link_url", ""),
                    game.get("image_url", ""), game.get("rating", ""),
                    game.get("mature_content", ""), now, now,
                ),
            )

    def commit(self):
        if self.connection is not None:
            self.connection.commit()

    def rollback(self):
        if self.connection is not None:
            self.connection.rollback()

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
