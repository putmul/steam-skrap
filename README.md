# SteamScrap

Scraper HTML Steam untuk mengambil base game yang memiliki tanggal rilis pasti pada H-1.

## Instalasi

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Jalankan `database/schema.sql` pada MariaDB, lalu pastikan nilai database pada `.env` benar.

## Menjalankan scheduler

```powershell
python -m stimskrapbot.scrapper
```

Scraper berjalan setiap pukul 02:00 dan menulis log ke `logs/steam_scraper.log`.

## Dry-run tanggal tertentu

```python
from datetime import date
from stimskrapbot.scrapper import SteamScraper

SteamScraper().run_daily_release_scraper(date(2026, 11, 14))
```

Hanya game dengan tanggal lengkap yang diproses. `Coming Soon`, `TBA`, tahun saja,
DLC, pack, soundtrack, bundle, demo, dan konten tambahan diabaikan.
