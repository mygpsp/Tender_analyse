#!/bin/bash
# Script to run detailed scraper on CON tenders

echo "Extracting tender numbers from con_filter.jsonl..."
python3 -c "
import json
tenders = []
with open('main_scrapper/data/con_filter.jsonl', 'r') as f:
    for line in f:
        if line.strip():
            data = json.loads(line)
            num = data.get('number', '').strip()
            if num:
                tenders.append(num)
print(' '.join(tenders))
" > /tmp/con_tender_numbers.txt

echo "Found $(wc -w < /tmp/con_tender_numbers.txt) tenders"
echo "Starting detailed scraper with 10 concurrent workers..."

# Run detailed scraper
python3 detailed_scraper/run_detailed_production.py \
  --tenders $(cat /tmp/con_tender_numbers.txt) \
  --concurrency 10 \
  --headless

echo "Detailed scraping complete!"
echo "Results saved to: main_scrapper/data/detailed_tenders.jsonl"
