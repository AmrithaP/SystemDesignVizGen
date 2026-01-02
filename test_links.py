from sdvg.pipeline.discover_links import discover_links

links = discover_links("uber", "HLD", max_links=5, allow_paywall=False)


print("\nFound links:")
for l in links:
    print("-", l)
