import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRAPER_ROOT = PROJECT_ROOT / "steam-skrap"
if str(SCRAPER_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRAPER_ROOT))
