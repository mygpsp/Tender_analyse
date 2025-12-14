# Supplier Scraper

Scrapes supplier profile data from the Georgian State Procurement Agency website.

## Features

- ✅ Navigates to Users → Suppliers section automatically
- ✅ Extracts supplier profile information from modals
- ✅ Handles pagination (62K+ suppliers across 4,148 pages)
- ✅ **Parallel scraping** with `--concurrency` flag for faster data collection
- ✅ Skips already scraped suppliers (based on identification code)
- ✅ Saves data to JSON Lines format
- ✅ Configurable via YAML selectors file
- ✅ Support for headless/non-headless mode

## Installation

The scraper uses the same dependencies as the main tender scraper:

```bash
pip install playwright pyyaml
playwright install chromium
```

## Usage

### Basic Usage

Scrape first page of suppliers:

```bash
cd Supplier_scrapping
python3 supplier_scraper.py
```

### Full Scale Scraping (Production)

For scraping the entire dataset (62,000+ suppliers), use the dedicated production script. This script is optimized for long-running execution and defaults to headless mode.

```bash
# Run full scrape in background (recommended)
nohup python3 run_full_scrape.py --concurrency 10 --max-pages 4200 > full_scrape.log 2>&1 &

# Check progress
tail -f full_scrape.log
```

**Options for `run_full_scrape.py`:**
- `--concurrency`: Number of parallel workers (default: 10)
- `--max-pages`: Maximum pages to scrape (default: 4200)
- `--output`: Output file path (default: `data/suppliers.jsonl`)
- `--visible`: Run with visible browser (for debugging)

### Parallel Scraping (Manual)

You can also run the base scraper with parallel options:

```bash
# Scrape first 100 pages with 5 parallel workers
python3 supplier_scraper.py --max-pages 100 --concurrency 5 --headless
```

**How Parallel Scraping Works:**
The scraper uses a **Round-Robin Page Scheduler**.
- Worker 1 scrapes pages: 1, 11, 21...
- Worker 2 scrapes pages: 2, 12, 22...
- This ensures no duplicate work and efficient distribution.

### Testing

Test the scraper with a small run:

```bash
python test_supplier_scraper.py
```

## Output Format

Data is saved in JSON Lines format (one JSON object per line):

```json
{
  "supplier": {
    "name": "Example Supplier",
    "identification_code": "123456789",
    "country": "Georgia",
    "city_or_region": "Tbilisi",
    "legal_address": "Rustaveli Ave 1",
    "telephone": "+995 555 00 00 00",
    "email": "info@example.com",
    "website": "http://example.com"
  },
  "contact_persons": [
    {
      "full_name": "John Doe",
      "position": "Director",
      "telephone": "555123456",
      "email": "john@example.com"
    }
  ],
  "cpv_codes": [
    {
      "code": "45000000",
      "description": "Construction work"
    }
  ],
  "registration_date": "01.01.2025",
  "supplier_or_buyer_type": "Supplier",
  "scraped_at": "2025-11-30T12:00:00",
  "scraping_status": "success"
}
```

## Configuration

Selectors and timing are configured in `config/supplier_selectors.yaml`:

- **Navigation selectors**: Users button, Suppliers tab
- **Table selectors**: Supplier rows, name cells
- **Modal selectors**: Dialog, close button, profile fields
- **Timing**: Page load timeouts, delays between actions

## Architecture

- **run_full_scrape.py**: Production entry point for full dataset scraping.
- **supplier_scraper.py**: Core scraper class with `PageScheduler` for round-robin assignment.
- **supplier_parser.py**: Extracts structured data (contacts, CPV codes) from profile modals.
- **config/supplier_selectors.yaml**: CSS/XPath selectors configuration.
- **test_parallel_last_150.py**: Integration test for parallel execution.

## Notes

- **Resilience**: Workers automatically retry navigation if it fails.
- **Deduplication**: Skips suppliers that have already been scraped (based on identification code).
- **Memory Management**: Modals are closed after each supplier to prevent leaks.

