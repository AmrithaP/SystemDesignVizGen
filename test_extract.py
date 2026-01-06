from sdvg.pipeline.discover_links import discover_links
from sdvg.pipeline.scrape import scrape_url
from sdvg.pipeline.extract_spec import extract_spec

topic = "uber"
level = "HLD"

links = discover_links(topic, level, max_links=4, allow_paywall=True)
pages = []
for l in links:
    try:
        pages.append(scrape_url(l))
    except Exception as e:
        print("SCRAPE FAILED:", l, e)

spec = extract_spec(topic, level, pages)
print(spec)
