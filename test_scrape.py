from sdvg.pipeline.discover_links import discover_links
from sdvg.pipeline.scrape import scrape_url

topic = "uber"
level = "HLD"

links = discover_links(topic, level,  max_links=12, max_results_per_query=20, allow_paywall=False)#max_links=5, allow_paywall=False)
print("\nLinks:")
for l in links:
    print("-", l)

print("\nScrape results:")
for l in links:
    try:
        page = scrape_url(l)
        print("\n===", page.title or "NO TITLE")
        print("URL:", page.url)
        print("Paywalled:", page.is_paywalled)
        print("Text chars:", len(page.text))
        print("Images:", len(page.images), "| Diagram score:", page.diagram_score)
        if page.images:
            top = page.images[0]
            print("Top image score:", top.score)
            print("Top image:", top.src)
        print("Text preview:", page.text[:300], "...")
    except Exception as e:
        print("FAILED:", l, e)
