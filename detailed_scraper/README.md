# Detailed Scraper

This module extracts detailed information from tender pages, including tabs (Documentation, Offers, Results).

## Production Runner (`run_detailed_production.py`)

This is the main entry point for running the detailed scraper in production.

### Usage

```bash
# Run with default settings (filter by status/date, 5 workers)
python3 detailed_scraper/run_detailed_production.py

# Run with 10 workers
python3 detailed_scraper/run_detailed_production.py --concurrency 10

# Run in INFO mode (count matching tenders without scraping)
python3 detailed_scraper/run_detailed_production.py --info

# Scrape specific tenders (overrides date/status filter)
python3 detailed_scraper/run_detailed_production.py --tenders GEO250000579 CON250000516

# Run in TEST mode (top 10 tenders only)
python3 detailed_scraper/run_detailed_production.py --test

# Clear existing data before running
python3 detailed_scraper/run_detailed_production.py --clear

# Force re-scrape of existing tenders (updates them in place)
python3 detailed_scraper/run_detailed_production.py --tenders GEO250000579 --force

# Filter by days (default 60)
python3 detailed_scraper/run_detailed_production.py --days 30

# Filter by specific date range
python3 detailed_scraper/run_detailed_production.py --date-from 2025-11-01 --date-to 2025-12-31

# Filter by relative dates
python3 detailed_scraper/run_detailed_production.py --date-from today --days 7
```

### Features

*   **Filtering**: Automatically filters tenders from `main_scrapper/data/tenders.jsonl` that:
    *   Are NOT "Winner Revealed", "Ended with negative result", or "Terminated".
    *   Have a deadline within the next 60 days (configurable via `--days`).
*   **Parallel Execution**: Runs multiple workers to scrape faster.
*   **Deduplication**: Automatically removes old records for a tender before writing the new one (update-in-place).
*   **Headless**: Runs without visible browser windows by default.
*   **Output**: Saves data to `main_scrapper/data/detailed_tenders.jsonl`.

## Scripts

*   `run_detailed_production.py`: Main orchestrator.
*   `filter_tenders.py`: Logic for filtering tenders from the main dataset.
*   `detail_scraper.py`: Core scraping logic (Playwright).
*   `config.yaml`: Configuration for selectors and timeouts.

## Data Format

Output is a JSONL file where each line is a JSON object containing:
*   `tender_number`: The unique identifier.
*   `tabs_data`: Dictionary containing text/HTML from each tab.
*   `scraped_at`: Timestamp.
