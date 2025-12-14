from app.services.supplier_loader import SupplierLoader
from pathlib import Path

# Mock data with quoted name as seen in previous outputs
mock_data = [
    {
        "supplier": {
            "name": "\" შპს მეგობრობა \"",
            "identification_code": "123456",
            "email": "test@example.com"
        }
    },
    {
        "supplier": {
            "name": "შპს მეგობრობა",
            "identification_code": "789012",
            "email": "other@example.com"
        }
    }
]

class MockLoader(SupplierLoader):
    def load_data(self):
        return mock_data

loader = MockLoader(Path("."))

def test_search(term):
    print(f"\n--- Searching for: '{term}' ---")
    results = loader.filter_suppliers(mock_data, search=term)
    print(f"Found {len(results)} matches")
    for s in results:
        print(f"Match: {s['supplier']['name']}")

test_search("შპს მეგობრობა")
test_search("მეგობრობა")
