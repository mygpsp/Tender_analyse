# Market Analysis Dashboard - Detailed Guide

## Overview
Analyzes Georgian government tenders with CPV code 60100000 (Automotive Transport Services).

## Data Scope

**Filter:** Only CPV 60100000 tenders
**Count:** ~798 tenders (from 10,000+ total)
**Date Range:** 2020-2025
**Types:** CON, NAT, SPA, GEO, DEP, CNT

## Features

### 1. KPI Cards
- **Total Tenders:** Count of CPV 60100000 tenders
- **Avg Inflation:** Average price inflation (2020-2025)
- **Market Volume:** Total estimated value in GEL

### 2. Price Evolution Chart
- Median prices by region and year
- Top 5 most active regions
- 5-year inflation rate per region

### 3. Competitor Market Share
- Top 10 winners by contract value
- Regions where each winner operates

### 4. Ghost Towns Chart
- Top 10 regions by failure rate
- Identifies problematic regions

### 5. Hot Opportunities Table
- Regions with >20% failure rate
- Potential re-tender opportunities

## Region Extraction

**Problem:** The `region` field in raw data is corrupt (18.6% are navigation menu errors).

**Solution:** Extract real region from document names, titles, and descriptions.

**Municipalities Searched:** 60+ including:
- თბილისი, ბათუმი, ქუთაისი, გორი, ზუგდიდი
- ხულო, შუახევი, ქობულეთი, ლანჩხუთი, ოზურგეთი
- მარტვილი, სენაკი, ხობი, წალენჯიხა, ჩხოროწყუ
- And 50+ more...

**Accuracy:** ~95% based on document naming conventions

## Price Calculations

**Method:** Median (not mean) to handle outliers

**Why Median?**
- Many tenders show per-km/per-unit prices (3-4 GEL/km)
- Some show total project values (100,000+ GEL)
- Median handles this mixed data better

**Example:**
```
ვანი Region 2025:
- Tender 1: 3.19 GEL/km
- Tender 2: 3.51 GEL/km
- Tender 3: 31,100 GEL (total project)
Median: 3.51 GEL (ignores outlier)
```

## Inflation Calculation

```python
inflation = ((latest_median - earliest_median) / earliest_median) * 100
```

**Example Results:**
- გორი: 108% (2020-2025) - Reliable (83 tenders in 2025)
- ხულო: 31% - Good data
- ქობულეთი: 18% - Realistic

## API Endpoints

```bash
# Get KPIs
curl http://localhost:8000/api/analysis/kpis

# Get price trends
curl http://localhost:8000/api/analysis/price-trends

# Get market share
curl http://localhost:8000/api/analysis/market-share

# Get failure rates
curl http://localhost:8000/api/analysis/failures

# Get hot opportunities
curl http://localhost:8000/api/analysis/hot-opportunities
```

## Data Quality Notes

### Per-Unit Pricing
Many automotive transport tenders show prices per km:
- CON250000330: 4.7 GEL/km
- CON200000225: 2.48 GEL/km
- CON210000227: 3.0 GEL/km

### Mixed Data
Some regions have both per-unit and total prices:
- ვანი: Mostly 3-4 GEL/km, one 31,100 GEL total
- გორი: Mix of 2-5 GEL/km and 100,000+ GEL totals

### Limited History
Some regions only have 2025 data:
- Makes inflation calculation unreliable
- Dashboard shows "N/A" for these regions

## Limitations

1. **Data Quality:** Prices represent different units
2. **Region Accuracy:** ~95% (some ambiguous names)
3. **Historical Data:** Limited before 2024 for some regions
4. **Outliers:** Median helps but doesn't eliminate all
5. **CPV Filter:** Only automotive transport (60100000)

## Future Enhancements

- Add filters for date range, tender type, CPV codes
- Export to Excel
- Drill-down to individual tenders
- ML-based outlier detection
- Year-over-year comparison mode
- Price normalization (per-km vs total)
