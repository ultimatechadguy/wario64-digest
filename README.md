# Wario64 Daily Deal Archive

Public archive: https://ultimatechadguy.github.io/wario64-digest/

## Fast model-readable feed

Use https://ultimatechadguy.github.io/wario64-digest/model/recent.txt for the last 48 hours,
`model/daily/YYYY-MM-DD.txt` for an exact completed daily window, or `model/latest.txt` for the latest completed window.
Each has an `.html` equivalent containing only escaped text, with no image tags, active links or media subresources.
`model/archive.txt` holds all retained posts. These versions include every post/repost with full untruncated text,
expanded links, original post URLs, author and timestamps, replies, nested quoted text, link-card titles and descriptions,
image alt text, video descriptions, and engagement counts. Avatars, image/thumbnail URLs, and media payloads are omitted.
Information present only in image pixels is unavailable unless the author supplied it as alt text; no OCR or image analysis is performed.
Use the dated or recent text file rather than loading the entire 30-day archive for a daily digest.

- GitHub Actions collects Wario64's public Bluesky feed every 15 minutes (`7,22,37,52`). No server, Bluesky login, API key, third-party subscription, or paid runner.
- Uses cursor pagination with 100 items per page, including replies and reposts. Initial collection backfills the last 30 days; later runs revisit a two-day overlap and paginate through longer outages.
- Deduplicates by post URI (plus repost event time), preserves full public API post records, and keeps a rolling 30-day current archive. Git history retains previous committed versions.
- Daily HTML and JSON windows run from the prior day's 4 PM to the labeled day's 4 PM in America/Los_Angeles, including daylight saving changes.
- `latest.html` and `latest.json`: latest completed 4 PM window. `recent.html`: last 48 hours, useful around the cutoff. `archive.json`: all retained events. `status.json`: update time and collection metadata. `daily/YYYY-MM-DD.html` and `.json`: dated digests.
- HTML includes post text, original links, external link cards, image alt text, and quoted text. Raw JSON preserves additional media metadata.

Standard GitHub-hosted Actions and Pages for this public repository are free. GitHub scheduling is best effort and may be delayed or disabled under GitHub policies. Each successful collection commits fresh state, maintaining repository activity. Check the Actions page if the public status timestamp becomes stale. Workflow failures preserve the previous successful archive.

This is an unofficial public-feed archive. It cannot capture posts deleted between polls or guarantee upstream API completeness; deleted records previously captured remain until they leave the rolling archive. Deal links may contain Wario64's affiliate tags. Do not assume an old deal is still available.

Run locally: Python 3.12+, `python scripts/archive.py`. Tests: `python -m unittest discover -s tests -v`.
