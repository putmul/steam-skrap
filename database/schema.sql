CREATE DATABASE IF NOT EXISTS steamscrap CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE steamscrap;

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
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS blocked_apps (
    app_id BIGINT PRIMARY KEY,
    alasan TEXT NOT NULL,
    blocked_at DATETIME NOT NULL
) CHARACTER SET utf8mb4;
