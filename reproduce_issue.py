
import re

def test_regex(regex_pattern, text, case_name):
    match = re.search(regex_pattern, text)
    if match:
        print(f"[{case_name}] MATCH: '{match.group(1).strip()}'")
    else:
        print(f"[{case_name}] NO MATCH")

# Regex from detail_parser.py
original_regex = r'შემსყიდველი[:\s]+([^\n(]+)'

# Proposed regex: Require colon or tab
# Note: \s includes \t, \n, \r, \f, \v
# We want to exclude simple space if it's not followed by colon or tab?
# Actually, the original regex was `[:\s]+` which means "one or more of colon or whitespace".
# "შემსყიდველი ორგანიზაცია" has a space, so it matches.
# We want to enforce that the separator MUST contain a colon or a tab.
# Or simply, it must be `:\s*` or `\t\s*`.
# Let's try `[:\t]` character class.

proposed_regex = r'შემსყიდველი\s*[:\t]\s*([^\n(]+)'

# Case 1: Incorrect match (from Documentation tab)
text_incorrect = """
4.1.1 მოთხოვნა ფასწარმოქმნის ადეკვატურობის დამადასტურებელი დოკუმენტ(ებ)ის შესახებ

იმ შემთხვევაში, თუ ტენდერში ყველაზე დაბალი ფასის წინადადების მქონე პრეტენდენტის მიერ სისტემაში დაფიქსირებული საბოლოო ფასი 20%-ით ან მეტით დაბალია შესყიდვის ობიექტის სავარაუდო ღირებულებაზე, შემსყიდველი ორგანიზაცია პრეტენდენტისაგან ითხოვს ფასწარმოქმნის ადეკვატურობის დასაბუთებას, რაზეც პრეტენდენტის მიერ წარმოდგენილი უნდა იქნას ექსპერტიზის ან აუდიტის მიერ გაცემული შესაბამისი დასკვნა
"""

# Case 2: Correct match (from Basic Info tab, with tab)
text_correct_tab = """
TAB: NAT250021092
შესყიდვის ტიპი	ელექტრონული ტენდერი აუქციონის გარეშე(NAT)
განცხადების ნომერი	NAT250021092
შესყიდვის სტატუსი	 წინადადებების მიღება დაწყებულია
შემსყიდველი	 საქ. ფინანსთა სამინისტროს საგამოძიებო სამსახური
შესყიდვის გამოცხადების თარიღი	24.11.2025 15:12
"""

# Case 3: Correct match (from Basic Info tab, with colon - assumed for NAT250021685 based on tenders.jsonl)
text_correct_colon = """
განცხადების ნომერი: NAT250021685

შესყიდვის გამოცხადების თარიღი: 28.11.2025

წინდადებების მიღების ვადა: 08.12.2025

შემსყიდველი: იუსტიციის სახლი

შესყიდვის კატეგორია: 72200000-პროგრამული უზრუნველყოფის შემუშავება და საკონსულტაციო მომსახურებები
"""

print("--- Testing Original Regex ---")
test_regex(original_regex, text_incorrect, "Incorrect Text")
test_regex(original_regex, text_correct_tab, "Correct Text (Tab)")
test_regex(original_regex, text_correct_colon, "Correct Text (Colon)")

print("\n--- Testing Proposed Regex ---")
test_regex(proposed_regex, text_incorrect, "Incorrect Text")
test_regex(proposed_regex, text_correct_tab, "Correct Text (Tab)")
test_regex(proposed_regex, text_correct_colon, "Correct Text (Colon)")
