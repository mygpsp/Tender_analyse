# Main Scrapper

Production-ready scraper for Georgian procurement tenders with headless multi-worker support.

## Quick Start

```bash
# Run with 10 workers (headless mode)
python3 main_scrapper/run_production.py --concurrency 10 --days 30

# Run in background
nohup python3 main_scrapper/run_production.py --concurrency 10 --days 30 > scraper.log 2>&1 &
```

## Features

- ✅ **Headless Mode** - No browser windows (runs in background)
- ✅ **Parallel Workers** - 10 workers scraping different date ranges simultaneously
- ✅ **Deadline Date Filtering** - Filters tenders by deadline dates
- ✅ **Auto-Deduplication** - Automatically skips existing tender numbers
- ✅ **Smart Date Detection** - Finds last scraped date and continues from there

## Directory Structure

```
main_scrapper/
├── config/
│   └── selectors.yaml          # CSS/XPath selectors
├── data/
│   └── tenders.jsonl          # Output data (auto-created)
├── main_scraper.py            # Core scraping logic
├── tender_scraper.py          # Tender scraper implementation
├── run_production.py          # Production script (headless)
├── PRODUCTION_GUIDE.md        # Detailed usage guide
└── README.md                  # This file
```

## Usage

### Production Scraping (Recommended)

**Run with 10 workers:**
```bash
python3 main_scrapper/run_production.py --concurrency 10 --days 30
```

**Custom date range:**
```bash
python3 main_scrapper/run_production.py \
  --concurrency 10 \
  --date-from 2025-01-01 \
  --date-to 2025-01-31
```

**Background execution:**
```bash
nohup python3 main_scrapper/run_production.py \
  --concurrency 10 \
  --days 30 \
  > logs/scraper_$(date +%Y%m%d).log 2>&1 &
```

### Command Options

| Option | Default | Description |
|--------|---------|-------------|
| `--concurrency` | 10 | Number of parallel workers |
| `--days` | 30 | Number of days to scrape from today |
| `--date-from` | Auto | Start date (YYYY-MM-DD) |
| `--date-to` | Auto | End date (YYYY-MM-DD) |
| `--data-file` | `main_scrapper/data/tenders.jsonl` | Output file |
| `--config` | `main_scrapper/config/selectors.yaml` | Config file |

### Monitoring

**Check if scraper is running:**
```bash
ps aux | grep run_production
```

**View live logs:**
```bash
tail -f scraper.log
```

**Check progress:**
```bash
# Count scraped tenders
wc -l main_scrapper/data/tenders.jsonl

# View last 10 tenders
tail -10 main_scrapper/data/tenders.jsonl
```

**Stop the scraper:**
```bash
# Find process ID
ps aux | grep run_production

# Kill it
kill <PID>
```

## How It Works

1. **Date Range Splitting**: The scraper divides the date range into chunks (one per worker)
2. **Parallel Execution**: Each worker scrapes a different date range simultaneously
3. **Deadline Date Filtering**: Filters tenders by their deadline dates (წინდადებების მიღების ვადა)
4. **Data Merging**: Results from all workers are merged into a single file
5. **Deduplication**: Backend automatically filters out invalid rows and duplicates

### Date Filtering

The scraper uses **deadline dates** for filtering. When you specify:
```bash
--date-from 2025-01-01 --date-to 2025-01-31
```

It will scrape all tenders with **deadline dates** between Jan 1 and Jan 31, 2025.

## Output Format

Data is saved to `main_scrapper/data/tenders.jsonl` in JSON Lines format:

```json
{
  "number": "NAT250000123",
  "buyer": "Company Name",
  "status": "გამოცხადებულია",
  "published_date": "2025-01-15",
  "deadline_date": "2025-01-30",
  "amount": 50000.0,
  "category": "45000000",
  "category_name": "სამშენებლო სამუშაოები",
  "detail_url": "https://tenders.procurement.gov.ge/public/?go=123456&lang=ge",
  "all_cells": "...",
  "scraped_at": 1234567890
}
```

## Data Validation

The backend automatically filters out:
- Navigation buttons (CMR, CON, SMP)
- Calendar date rows
- Header rows
- Empty rows
- Rows without valid tender numbers

**Example:**
- Raw file: 3246 lines
- Valid tenders: 2156 records
- Filtered out: ~1090 invalid rows

This is normal and expected behavior.

## Performance

- **10 workers** is optimal for most systems
- **Headless mode** uses ~50% less memory than visible browsers
- **Average speed**: ~100-200 tenders per minute (depends on network)
- **Memory usage**: ~500MB per worker

## Troubleshooting

**Issue: Browsers still opening**
- Solution: Make sure you're using `run_production.py` (not `main_scraper.py` directly)

**Issue: "No module named 'main_scraper'"**
- Solution: Run from project root directory

**Issue: Too many browser instances**
- Solution: Reduce `--concurrency` to 5 or fewer

**Issue: Scraper stops unexpectedly**
- Solution: Check `scraper.log` for errors
- Try reducing concurrency or date range

## Integration with Backend

The backend automatically reads from `main_scrapper/data/tenders.jsonl`. No configuration needed.

To refresh data in the frontend:
1. Restart the backend server (it will reload data)
2. Or call the cache clear endpoint: `POST /api/analytics/clear-cache`

## See Also

- [Production Guide](PRODUCTION_GUIDE.md) - Detailed usage guide
- [Main README](../README.md) - Project overview
- [Backend README](../backend/README.md) - API documentation
- [Frontend README](../frontend/README.md) - UI documentation
