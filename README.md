# Wario64 Daily Deal Archive

Public archive: https://ultimatechadguy.github.io/wario64-digest/

- GitHub Actions collects Wario64's public Bluesky feed every 15 minutes (`7,22,37,52`). No server, Bluesky login, API key, third-party subscription, or paid runner.
- Uses cursor pagination with 100 items per page, including replies and reposts. Initial collection backfills the last 30 days; later runs revisit a two-day overlap and paginate through longer outages.
- Deduplicates by post URI (plus repost event time), preserves full public API post records, and keeps a rolling 30-day current archive. Git history retains previous committed versions.
- Daily HTML and JSON windows run from the prior day's 4 PM to the labeled day's 4 PM in America/Los_Angeles, including daylight saving changes.
- `latest.html` and `latest.json`: latest completed 4 PM window. `recent.html`: last 48 hours, useful around the cutoff. `archive.json`: all retained events. `status.json`: update time and collection metadata. `daily/YYYY-MM-DD.html` and `.json`: dated digests.
- HTML includes post text, original links, external link cards, image alt text, and quoted text. Raw JSON preserves additional media metadata.

Standard GitHub-hosted Actions and Pages for this public repository are free. GitHub scheduling is best effort and may be delayed or disabled under GitHub policies. Each successful collection commits fresh state, maintaining repository activity. Check the Actions page if the public status timestamp becomes stale. Workflow failures preserve the previous successful archive.

This is an unofficial public-feed archive. It cannot capture posts deleted between polls or guarantee upstream API completeness; deleted records previously captured remain until they leave the rolling archive. Deal links may contain Wario64's affiliate tags. Do not assume an old deal is still available.

Run locally: Python 3.12+, `python scripts/archive.py`. Tests: `python -m unittest discover -s tests -v`.
