from app.services.supplier_loader import SupplierLoader
from pathlib import Path
import logging

# Mock data
mock_data = [
    {"supplier": {"name": "C Company", "identification_code": "300", "registration_date": "01.01.2022"}},
    {"supplier": {"name": "A Company", "identification_code": "100", "registration_date": "01.01.2020"}},
    {"supplier": {"name": "B Company", "identification_code": "200", "registration_date": "01.01.2021"}},
]

class MockLoader(SupplierLoader):
    def load_data(self):
        return mock_data

loader = MockLoader(Path("."))

def test_sort(field, order):
    print(f"--- Sorting by {field} ({order}) ---")
    results = loader.filter_suppliers(mock_data, sort_by=field, sort_order=order)
    for s in results:
        val = s['supplier'].get('name' if field == 'name' else 'identification_code' if field == 'id' else 'registration_date')
        print(val)

test_sort("name", "asc")
test_sort("name", "desc")
test_sort("date", "asc")
test_sort("date", "desc")
test_sort("id", "asc")
test_sort("id", "desc")
