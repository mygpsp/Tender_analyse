#!/usr/bin/env python3
"""
Process existing detailed_tenders.jsonl to add parsed data.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from detail_parser import parse_tender_detail

def process_file(input_path: Path, output_path: Path):
    """Process existing JSONL file and add parsed data."""
    processed = []
    
    with open(input_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                data = json.loads(line.strip())
                
                # Skip if already has parsed data
                if 'basic_info' in data and data.get('basic_info'):
                    print(f"Line {line_num}: Already has parsed data, skipping")
                    processed.append(data)
                    continue
                
                # Parse the data
                html = data.get('html_content', '')
                text = data.get('full_text', '')
                
                if not text:
                    print(f"Line {line_num}: No text content, skipping")
                    processed.append(data)
                    continue
                
                print(f"Line {line_num}: Processing {data.get('tender_number', 'unknown')}...")
                parsed = parse_tender_detail(html, text)
                
                # Merge parsed data into existing record
                data.update({
                    'basic_info': parsed.get('basic_info', {}),
                    'description': parsed.get('description', ''),
                    'specifications': parsed.get('specifications', ''),
                    'documents': parsed.get('documents', []) or data.get('documents', []),
                    'timeline': parsed.get('timeline', []),
                    'contacts': parsed.get('contacts', {}),
                    'terms': parsed.get('terms', ''),
                    'deadlines': parsed.get('deadlines', {}),
                    'all_sections': parsed.get('structured_data', {}),
                })
                
                # Update tender_link if parsed found one
                if parsed.get('tender_link') and not data.get('tender_link'):
                    data['tender_link'] = parsed.get('tender_link')
                
                processed.append(data)
                print(f"  ✅ Extracted: buyer={bool(parsed.get('basic_info', {}).get('buyer'))}, "
                      f"category={bool(parsed.get('basic_info', {}).get('category'))}, "
                      f"amount={bool(parsed.get('basic_info', {}).get('amount'))}")
                
            except Exception as e:
                print(f"Line {line_num}: Error - {e}")
                processed.append(data)  # Keep original
                continue
    
    # Write processed data
    with open(output_path, 'w', encoding='utf-8') as f:
        for record in processed:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"\n✅ Processed {len(processed)} records")
    print(f"✅ Saved to {output_path}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='data/detailed_tenders.jsonl')
    parser.add_argument('--output', default='data/detailed_tenders.jsonl')
    args = parser.parse_args()
    
    process_file(Path(args.input), Path(args.output))

