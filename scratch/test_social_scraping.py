import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.scraper import LeadGenerator

mock_html = """
<html>
  <body>
    <footer>
      <a href="https://facebook.com/MahindraRise">Facebook</a>
      <a href="https://x.com/MahindraRise">Twitter X</a>
      <a href="https://instagram.com/mahindrarise">Instagram</a>
      <a href="https://youtube.com/mahindrarise">YouTube</a>
      <a href="https://linkedin.com/company/mahindra-group">LinkedIn</a>
    </footer>
  </body>
</html>
"""

lg = LeadGenerator.__new__(LeadGenerator)
extracted = lg._extract_social_links(mock_html)

print("Extracted Social Links from DOM:")
print(extracted)

assert extracted.get("facebook") == "https://facebook.com/MahindraRise"
assert extracted.get("twitter") == "https://x.com/MahindraRise"
assert extracted.get("instagram") == "https://instagram.com/mahindrarise"
assert extracted.get("youtube") == "https://youtube.com/mahindrarise"
assert extracted.get("company_linkedin") == "https://linkedin.com/company/mahindra-group"

print("\nSOCIAL MEDIA DOM EXTRACTION PASSED 100% SUCCESSFULLY!")
