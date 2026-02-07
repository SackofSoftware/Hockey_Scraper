import asyncio
from playwright.async_api import async_playwright

SITES = [
    "https://www.lynnfieldyouthhockey.com/",
    "https://mryha.org/",
    "https://providencehockeyclub.com/",
    "https://www.tricountysaints.com/",
    "https://www.braintreeyouthhockey.org/",
    "https://capecodcanalyouthhockey.sportngin.com/",
    "https://www.hinghamyouthhockey.com/",
    "https://www.ydyouthhockey.com/",
    "https://www.duxburyyouthhockey.org/",
    "https://www.pembrokeyouthhockey.com/",
    "https://www.massadmirals.com/",
]

PLATFORM_CHECKS = {
    "SportsEngine": ["sportngin", "sportsengine", "theme-nav-item", "se-widget"],
    "Crossbar": ["crossbar"],
    "LeagueApps": ["leagueapps", "/clubteams/", "la-team"],
    "Angular": ["ng-star-inserted", "angular", "ng-version"],
}


async def probe_site(browser, url):
    result = {"url": url, "title": "", "platform": "Unknown", "indicators": [], "team_links": 0, "error": None}
    page = None
    try:
        page = await browser.new_page()
        page.set_default_timeout(30000)
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # Give JS a moment to render
        await page.wait_for_timeout(3000)

        result["title"] = await page.title()
        html = (await page.content()).lower()

        # Detect platform
        for platform, keywords in PLATFORM_CHECKS.items():
            matched = [kw for kw in keywords if kw in html]
            if matched:
                result["platform"] = platform
                result["indicators"] = matched
                break  # first match wins

        # Count links that look like team pages
        links = await page.query_selector_all("a[href]")
        team_keywords = ["team", "roster", "schedule", "division", "league"]
        count = 0
        for link in links:
            href = (await link.get_attribute("href") or "").lower()
            text = (await link.inner_text() or "").lower().strip()
            if any(kw in href or kw in text for kw in team_keywords):
                count += 1
        result["team_links"] = count

    except Exception as e:
        result["error"] = str(e)
    finally:
        if page:
            await page.close()
    return result


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        tasks = [probe_site(browser, url) for url in SITES]
        results = await asyncio.gather(*tasks)
        await browser.close()

    print("=" * 90)
    print(f"{'URL':<50} {'Platform':<15} {'Team Links':<12} {'Indicators'}")
    print("=" * 90)
    for r in results:
        short_url = r["url"].replace("https://", "").replace("http://", "").rstrip("/")
        if r["error"]:
            print(f"{short_url:<50} {'ERROR':<15} {'':<12} {r['error'][:40]}")
        else:
            indicators_str = ", ".join(r["indicators"]) if r["indicators"] else "-"
            print(f"{short_url:<50} {r['platform']:<15} {r['team_links']:<12} {indicators_str}")
    
    print("\n" + "=" * 90)
    print("DETAILED RESULTS")
    print("=" * 90)
    for r in results:
        short_url = r["url"].replace("https://", "").replace("http://", "").rstrip("/")
        print(f"\n--- {short_url} ---")
        print(f"  Title:      {r['title']}")
        print(f"  Platform:   {r['platform']}")
        print(f"  Indicators: {r['indicators']}")
        print(f"  Team Links: {r['team_links']}")
        if r["error"]:
            print(f"  Error:      {r['error']}")


if __name__ == "__main__":
    asyncio.run(main())
