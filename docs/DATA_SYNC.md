# Data Sync System - Detailed Guide

## Overview
Automated system for keeping tender data up-to-date with two-phase synchronization.

## How It Works

### Phase A: Active Tender Re-check
- Loads existing data
- Filters for active statuses (6 types)
- Filters for last 60 days
- Re-scrapes to detect status changes
- Example: 153 active tenders re-checked

### Phase B: New Tender Fetch
- Finds max `published_date` in data
- Sets range: max_date+1 to today
- Fetches only new tenders
- Example: 2025-12-04 to 2025-12-08

## Usage

### Manual Run
```bash
# Default (CON detailed tenders)
python3 data_updater.py

# Specific file
python3 data_updater.py nat_detailed_tenders.jsonl
```

### Scheduled Run
```bash
# Cron: Daily at 2 AM
0 2 * * * cd /path/to/project && python3 data_updater.py >> logs/cron.log 2>&1

# Systemd timer (create /etc/systemd/system/tender-sync.service)
[Unit]
Description=Tender Data Sync

[Service]
Type=oneshot
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python3 data_updater.py

[Install]
WantedBy=multi-user.target
```

## Monitoring

### Frontend Dashboard
**Access:** `http://localhost:3000/system-health`

**Features:**
- Green/Red/Yellow status indicator
- Last run time
- New tenders added
- Status changes detected
- Active tenders re-checked
- Last 10 run logs (expandable)

### API Endpoints
```bash
# Get update logs
curl http://localhost:8000/api/system/update-logs

# Get system health
curl http://localhost:8000/api/system/health
```

## Log Format

**File:** `logs/update_history.json`

```json
{
  "run_id": "8a52d46b-0221-409d-a6dc-03eb13d70b5d",
  "timestamp": "2025-12-08T22:53:40.253000",
  "status": "SUCCESS",
  "metrics": {
    "total_active_rechecked": 153,
    "status_changes_detected": 0,
    "new_tenders_added": 0,
    "total_tenders": 913,
    "errors": []
  },
  "duration_seconds": 1.01,
  "data_file": "con_detailed_tenders.jsonl"
}
```

## Status Definitions

Loaded from `main_scrapper/data/tender_statuses.json`:

**Active Statuses (Need Re-check):**
1. გამოცხადებულია (Announced)
2. წინადადებების მიღება დაწყებულია (Accepting Proposals)
3. წინადადებების მიღება დასრულებულია (Deadline Passed)
4. შერჩევა/შეფასება (Evaluation)
5. გამარჯვებული გამოვლენილია (Winner Announced)
6. მიმდინარეობს ხელშეკრულების მომზადება (Contract Preparation)

**Final Statuses (Stop Checking):**
1. ხელშეკრულება დადებულია (Contract Signed)
2. არ შედგა (Failed)
3. დასრულებულია უარყოფითი შედეგით (Negative Result)
4. შეწყვეტილია (Terminated)

## Integration with Scrapers

**Current:** Uses mock functions (no actual scraping)

**To Enable Real Scraping:**

Edit `data_updater.py`:

```python
def scrape_tenders_by_ids(self, tender_ids: List[str]) -> List[Dict[str, Any]]:
    """Scrape tenders by IDs."""
    from detailed_scraper.run_detailed_production import scrape_by_ids
    return scrape_by_ids(tender_ids)

def scrape_tenders_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """Scrape tenders by date range."""
    from main_scrapper.tender_scraper import scrape_by_date_range
    return scrape_by_date_range(start_date, end_date)
```

## Error Handling

- **File Not Found:** Creates new file on first run
- **Scraper Failure:** Logs error, continues with partial data
- **Invalid JSON:** Skips malformed records
- **Disk Full:** Checks before writing
- **Network Error:** Retries with exponential backoff

## Performance

- **Load Time:** ~0.4s for 913 tenders
- **Update Time:** ~1s (no actual scraping)
- **Memory:** ~50MB for 10,000 tenders
- **Disk:** Temp file = 2x data size

## Troubleshooting

**No logs appearing:**
```bash
# Check logs directory exists
ls -la logs/

# Check permissions
chmod 755 logs/
```

**Status not updating:**
```bash
# Check if scraper functions are mocked
grep "mock scraper" data_updater.py

# Enable real scrapers (see Integration section)
```

**Dashboard shows "No Data":**
```bash
# Run updater at least once
python3 data_updater.py

# Check log file exists
cat logs/update_history.json
```

## Advanced Configuration

### Custom Date Range
```python
# In data_updater.py, modify phase_b_fetch_new():
start_date = end_date - timedelta(days=7)  # Last 7 days only
```

### Custom Active Window
```python
# Modify phase_a_recheck_active():
cutoff_date = datetime.now() - timedelta(days=30)  # 30 days instead of 60
```

### Multiple Files
```bash
# Create wrapper script
for file in con nat spa geo; do
    python3 data_updater.py ${file}_detailed_tenders.jsonl
done
```
