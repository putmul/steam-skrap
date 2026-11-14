# SteamScrap

Scraper HTML Steam sederhana untuk mengambil base game yang memiliki tanggal rilis
pasti pada H-1.

Sumber yang digunakan:

- daftar game: `https://store.steampowered.com/search/?sort_by=Released_DESC&page={page}`
- detail game: `https://store.steampowered.com/app/{app_id}/`
- izin scraping: `https://store.steampowered.com/robots.txt`

## Instalasi

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Jalankan `database/schema.sql` pada MariaDB, lalu atur `DB_HOST`, `DB_PORT`, `DB_NAME`,
`DB_USER`, dan `DB_PASSWORD` bila diperlukan pada `.env`.

Sebelum halaman Steam diambil, program selalu memeriksa `robots.txt`. Jika tidak dapat
diperiksa atau URL dilarang, proses dihentikan.

## Menjalankan

```powershell
python main.py --test-scrape  # maksimal lima game valid dari H-1
python main.py --once         # seluruh game valid dari H-1
python main.py --schedule     # otomatis setiap 02:00 WIB
```

## Menjalankan scheduler

```powershell
python main.py --schedule
```

Scraper berjalan setiap pukul 02:00 dan menulis log ke `logs/steam_scraper.log`.

## Menjalankan untuk tanggal tertentu

```python
from datetime import date
from main import jalankan_pipeline

jalankan_pipeline(target_date=date(2026, 11, 13), limit=5)
```

Hanya game dengan tanggal lengkap yang diproses. `Coming Soon`, `TBA`, tahun saja,
DLC, pack, soundtrack, bundle, demo, dan konten tambahan diabaikan.
