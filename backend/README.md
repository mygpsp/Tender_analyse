# Tender Analysis Backend

FastAPI backend application for analyzing scraped tender data.

## Setup

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure the data directory exists with JSONL files:
```
../../data/tenders.jsonl
```

## Running the Server

### Development
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Tenders
- `GET /api/tenders` - List tenders with pagination and filtering
  - Query params: `page`, `page_size`, `buyer`, `status`, `date_from`, `date_to`, `filter_by_published_date`, `filter_by_deadline_date`, `search`, `amount_min`, `amount_max`, `tender_number`, `has_detailed_data`
- `GET /api/tenders/{id}` - Get specific tender by ID

### Analytics
- `GET /api/analytics/summary` - Overall statistics with optional filters
  - Query params: `buyer`, `status`, `date_from`, `date_to`, `filter_by_published_date`, `filter_by_deadline_date`, `search`, `amount_min`, `amount_max`
- `GET /api/analytics/by-buyer` - Statistics grouped by buyer
- `GET /api/analytics/by-category` - Statistics grouped by category
- `GET /api/analytics/by-winner` - Statistics grouped by winner/supplier
- `GET /api/analytics/timeline` - Timeline analysis
- `POST /api/analytics/clear-cache` - Clear analytics cache

### Detailed Tenders
- `GET /api/detailed-tenders/list` - List detailed tender records
  - Query params: `tender_number`, `limit`, `offset`
- `GET /api/detailed-tenders/{tender_number}` - Get detailed data for a specific tender
- `GET /api/detailed-tenders/tender-numbers` - Get list of all tender numbers with detailed data
- `POST /api/detailed-tenders/reload` - Reload detailed tender data from file
- `DELETE /api/detailed-tenders/{tender_number}` - Delete detailed data for a specific tender

## Configuration

The backend expects data files in `../../data/` relative to the backend directory.
You can modify the data path in `app/services/data_loader.py` if needed.

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── api/                  # API routes
│   │   ├── tenders.py       # Tender listing and filtering endpoints
│   │   ├── analytics.py     # Analytics endpoints (summary, by-buyer, by-category, by-winner, timeline)
│   │   └── detailed_tenders.py  # Detailed tender data endpoints
│   ├── services/            # Business logic services
│   │   ├── data_loader.py   # Loads and caches main tender data from JSONL files
│   │   ├── analytics.py     # Analytics calculations and filtering
│   │   └── detail_loader.py # Loads and caches detailed tender data
│   └── models/              # Pydantic models
│       └── tender.py       # Data models (Tender, TenderResponse, AnalyticsSummary, etc.)
├── requirements.txt         # Python dependencies
└── README.md
```

