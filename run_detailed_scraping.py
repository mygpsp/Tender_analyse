#!/usr/bin/env python3
"""
Detailed Scraping Runner
------------------------
Unified script to run detailed scraping in two modes:
1. Date Range: Scrapes all tenders within a specific date range.
   Usage: python3 run_detailed_scraping.py --date-from YYYY-MM-DD --date-to YYYY-MM-DD

2. Default (Active Check): Scrapes all ACTIVE tenders (deadline >= today) that are missing details.
   Usage: python3 run_detailed_scraping.py
"""
import argparse
import subprocess
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('detailed_run')

PROJECT_ROOT = Path(__file__).resolve().parent

def run_date_range_mode(date_from: str, date_to: str, force: bool = False):
    """
    Run the scraper for a specific date range.
    Uses detailed_scraper/run_detailed_production.py
    """
    logger.info("=" * 60)
    logger.info(f"📅 MODE: Date Range Scraping")
    logger.info(f"   From:  {date_from}")
    logger.info(f"   To:    {date_to}")
    logger.info(f"   Force: {force}")
    logger.info("=" * 60)
    
    script_path = PROJECT_ROOT / "detailed_scraper" / "run_detailed_production.py"
    
    cmd = [
        sys.executable,
        str(script_path),
        "--date-from", date_from,
        "--date-to", date_to,
        "--headless" # Default to headless
    ]
    
    if force:
        cmd.append("--force")
    
    try:
        # Run the command and wait for it to finish
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Date range scraping completed successfully.")
        else:
            logger.error(f"❌ Date range scraping failed with code {result.returncode}.")
            
    except Exception as e:
        logger.error(f"Error running scraper: {e}")

def run_default_mode(force: bool = False):
    """
    Run the default check for 'Active & Missing Details' tenders.
    Uses update_detailed_tenders.py which implements this logic.
    """
    logger.info("=" * 60)
    logger.info(f"⚡ MODE: Default / Active Tenders Audit")
    logger.info(f"   Action: Checking all active tenders (deadline >= today) for missing details.")
    if force:
        logger.info("   Note: 'force' argument is currently only supported in date-range mode.")
        logger.info("         Default mode only fills missing data gaps.")
    logger.info("=" * 60)
    
    script_path = PROJECT_ROOT / "update_detailed_tenders.py"
    
    cmd = [
        sys.executable,
        str(script_path)
    ]
    
    try:
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Active tenders check completed successfully.")
        else:
            logger.error(f"❌ Active tenders check failed with code {result.returncode}.")
            
    except Exception as e:
        logger.error(f"Error running updater: {e}")

def main():
    parser = argparse.ArgumentParser(description="Run Detailed Scraping Job")
    
    parser.add_argument(
        "--date-from", 
        dest="date_from",
        help="Start date (YYYY-MM-DD) for range scraping",
        default=None
    )
    
    parser.add_argument(
        "--date-to", 
        dest="date_to", 
        help="End date (YYYY-MM-DD) for range scraping",
        default=None
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-scraping even if data exists (Date Range mode only)",
        default=False
    )
    
    args = parser.parse_args()
    
    # Logic: If dates are provided, use range mode. Otherwise, use default active check mode.
    if args.date_from or args.date_to:
        if not args.date_from or not args.date_to:
            logger.error("❌ Error: Both --date-from and --date-to are required for date range mode.")
            return
            
        run_date_range_mode(args.date_from, args.date_to, args.force)
    else:
        run_default_mode(args.force)

    # Always run merge step at the end to ensure data visibility
    logger.info("=" * 60)
    logger.info("🔄 Running Merge Step...")
    try:
        merge_script = PROJECT_ROOT / "detailed_scraper" / "merge_detailed_files.py"
        subprocess.run([sys.executable, str(merge_script)], cwd=PROJECT_ROOT, check=True)
    except Exception as e:
        logger.error(f"❌ Merge step failed: {e}")

if __name__ == "__main__":
    main()
