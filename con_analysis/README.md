# CON Tender Analysis Module

This module provides utilities for analyzing CON (Consolidated) tenders, specifically focusing on category code 60100000 (Automotive Transport Services).

## Directory Structure

```
con_analysis/
├── __init__.py                    # Package initialization
├── filter_con_tenders.py          # Filter CON tenders from main data
├── check_detailed_data.py         # Check for missing detailed data
├── scrape_missing.py              # Scrape missing detailed tenders
├── extract_region.py              # Extract region from descriptions
├── parse_final_price.py           # Parse final price from detailed data
├── test_region_extraction.py      # Test region extraction logic
├── README.md                      # This file
└── data/                          # Output data files
    ├── con_tenders_60100000.jsonl # Filtered CON tenders
    ├── con_tenders_enriched.jsonl # Enriched with detailed data
    └── missing_detailed_tenders.txt # List of missing tenders
```

## Usage

### 1. Filter CON Tenders

Filter CON tenders with category code 60100000 from the main data:

```bash
python3 con_analysis/filter_con_tenders.py
```

This will create `con_analysis/data/con_tenders_60100000.jsonl` with filtered tenders.

### 2. Check for Missing Detailed Data

Identify which CON tenders are missing detailed data:

```bash
python3 con_analysis/check_detailed_data.py
```

This will create `con_analysis/data/missing_detailed_tenders.txt` with a list of tender numbers.

### 3. Scrape Missing Data (Optional)

If you need to scrape missing detailed data:

```bash
python3 con_analysis/scrape_missing.py --concurrency 5
```

### 4. Test Region Extraction

Test the region extraction logic:

```bash
python3 con_analysis/test_region_extraction.py
```

## Region Extraction

The region extraction logic identifies Georgian municipalities from tender descriptions using regex patterns.

**Examples:**
- "ზუგდიდის მუნიციპალიტეტის სკოლების..." → "ზუგდიდი"
- "თბილისის მუნიციპალიტეტის..." → "თბილისი"
- "ბათუმის მუნიციპალიტეტის..." → "ბათუმი"

The logic supports 50+ Georgian municipalities and handles various grammatical cases.

## Data Fields

The CON tender analysis includes the following fields:

- **Tender Number**: Unique identifier (e.g., CON240000666)
- **Date Bidding**: Published date (published_date)
- **Initial Price**: Estimated value (amount)
- **Final Price**: Contract amount or winning bid (from detailed data)
- **Winner**: Supplier name (from detailed data)
- **Region**: Municipality name (extracted from description)
- **Status**: Tender status

## API Endpoints

The backend provides the following API endpoints:

- `GET /api/con-tenders` - List CON tenders with pagination and filtering
- `GET /api/con-tenders/stats` - Statistics for CON tenders
- `GET /api/con-tenders/export` - Export CON tenders to Excel

See the backend API documentation for more details.
