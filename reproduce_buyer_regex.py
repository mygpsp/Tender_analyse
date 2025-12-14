import re

def test_regex():
    # Test cases
    correct_text = "შემსყიდველი\tიუსტიციის სახლი\nსხვა ინფორმაცია..."
    problematic_text = "4.1.1 ... შემსყიდველი ორგანიზაცია პრეტენდენტისაგან ითხოვს ფასწარმოქმნის ადეკვატურობის დასაბუთებას ..."
    mixed_text = "შემსყიდველი\tიუსტიციის სახლი\n4.1.1 ... შემსყიდველი ორგანიზაცია პრეტენდენტისაგან ითხოვს ..."

    # Old regex
    old_pattern = r'შემსყიდველი[:\s]+([^\n(]+)'
    
    # New regex (stricter)
    # Matches colon, tab, or 2+ spaces
    new_pattern = r'შემსყიდველი(?:[:\t]|[ \t]{2,})([^\n(]+)'

    print("--- Testing Old Regex ---")
    match = re.search(old_pattern, correct_text)
    print(f"Correct text match: '{match.group(1).strip()}'" if match else "No match")
    
    match = re.search(old_pattern, problematic_text)
    print(f"Problematic text match: '{match.group(1).strip()}'" if match else "No match")

    print("\n--- Testing New Regex ---")
    match = re.search(new_pattern, correct_text)
    print(f"Correct text match: '{match.group(1).strip()}'" if match else "No match")
    
    match = re.search(new_pattern, problematic_text)
    print(f"Problematic text match: '{match.group(1).strip()}'" if match else "No match")
    
    match = re.search(new_pattern, mixed_text)
    print(f"Mixed text match: '{match.group(1).strip()}'" if match else "No match")

if __name__ == "__main__":
    test_regex()
