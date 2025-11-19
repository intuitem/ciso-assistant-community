"""
Web Scraper for ANSSI AD Framework (v0.1)

This scraper extract the content of the website and store it in a JSON file.
TODO: Format text in Markdown according to the HTML tags and store it correctly in an Excel (.xlsx) file. 
"""



import json
from playwright.sync_api import sync_playwright

URL = "https://www.cert.ssi.gouv.fr/uploads/ad_checklist.html"

def extract_checklist():
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(URL, wait_until="load")

        # Wait until at least one header TR is mounted
        page.wait_for_selector("div#root table tbody tr td:nth-child(2)")

        # Retrieve all TR elements
        rows = page.query_selector_all("div#root table tbody tr")

        i = 0
        while i < len(rows):
            row = rows[i]
            cells = row.query_selector_all("td")

            # A header row has >= 3 visible cells
            if len(cells) >= 3:
                level = cells[0].inner_text().strip()
                title = cells[1].inner_text().strip()
                identifier = cells[-1].inner_text().strip()

                # Description row (next row, 1 cell + hidden)
                description = ""
                recommendation = ""

                if i + 1 < len(rows):
                    desc_row = rows[i + 1]
                    if desc_row.get_attribute("hidden") is not None:
                        description = desc_row.inner_text().strip()

                if i + 2 < len(rows):
                    reco_row = rows[i + 2]
                    if reco_row.get_attribute("hidden") is not None:
                        recommendation = reco_row.inner_text().strip()

                results.append({
                    "level": level,
                    "title": title,
                    "identifier": identifier,
                    "description": description,
                    "recommendation": recommendation,
                })

                i += 3  # Skip the two hidden rows linked to the header row
            else:
                i += 1

        browser.close()

    return results


if __name__ == "__main__":
    data = extract_checklist()

    print(f"Number of checklist items found: {len(data)}\n")
    for entry in data[:5]:
        print("Level:", entry["level"])
        print("Title:", entry["title"])
        print("ID:", entry["identifier"])
        print("Description:", entry["description"][:200], "...")
        print("Recommendation:", entry["recommendation"][:200], "...")
        print("-" * 80)
        
    # --- Save JSON ---
    with open("checklist_raw.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print("\n✓ JSON file saved: checklist_raw.json")
