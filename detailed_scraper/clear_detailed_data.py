#!/usr/bin/env python3
"""
Utility script to clear detailed tender data file.

Usage:
    python3 clear_detailed_data.py [--file path/to/detailed_tenders.jsonl]
"""
import argparse
import shutil
from pathlib import Path


def clear_detailed_data(file_path: Path, create_backup: bool = True) -> None:
    """
    Clear the detailed tenders JSONL file.
    
    Args:
        file_path: Path to the detailed_tenders.jsonl file
        create_backup: If True, create a backup before clearing
    """
    if not file_path.exists():
        print(f"⚠️  File does not exist: {file_path}")
        return
    
    # Count lines before clearing
    line_count = sum(1 for _ in file_path.open('r', encoding='utf-8'))
    
    if create_backup:
        backup_path = file_path.with_suffix('.jsonl.bak')
        shutil.copy(file_path, backup_path)
        print(f"✅ Created backup: {backup_path}")
    
    # Clear the file
    file_path.write_text('', encoding='utf-8')
    print(f"✅ Cleared {line_count} records from: {file_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clear detailed tender data file"
    )
    parser.add_argument(
        "--file",
        default="data/detailed_tenders.jsonl",
        help="Path to detailed_tenders.jsonl file (default: data/detailed_tenders.jsonl)"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create a backup before clearing"
    )
    
    args = parser.parse_args()
    file_path = Path(args.file)
    
    print(f"Clearing detailed data from: {file_path}")
    clear_detailed_data(file_path, create_backup=not args.no_backup)
    print("✅ Done!")


if __name__ == "__main__":
    main()

