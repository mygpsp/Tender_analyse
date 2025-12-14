#!/bin/bash
TENDERS=$(head -100 missing_con_tenders.txt | tr '\n' ' ')
python3 detailed_scraper/run_detailed_production.py --tenders $TENDERS --concurrency 10 --headless
