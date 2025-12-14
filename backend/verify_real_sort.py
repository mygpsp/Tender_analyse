from app.services.supplier_loader import SupplierLoader
from pathlib import Path
import logging

# Setup loader with real path
data_path = Path("../Supplier_scrapping/data/suppliers.jsonl").absolute()
print(f"Loading data from {data_path}")
loader = SupplierLoader(data_path)
data = loader.load_data()
print(f"Loaded {len(data)} suppliers")

def test_sort(order):
    print(f"\n--- Sorting by date ({order}) ---")
    results = loader.filter_suppliers(data, sort_by="date", sort_order=order)
    for i, s in enumerate(results[:5]):
        print(f"{i+1}. {s['supplier'].get('registration_date')}")

test_sort("asc")
test_sort("desc")
