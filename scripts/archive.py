#!/usr/bin/env python3
"""Public Bluesky collector and server-rendered digest. Python standard library only."""
import html
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ACTOR = 'did:plc:knj5sw5al3sukl6vhkpi7637'
HANDLE = 'wario64.bsky.social'
PACIFIC = ZoneInfo('America/Los_Angeles')
UTC = timezone.utc

def dt(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))

def stamp(value):
    return value.astimezone(UTC).isoformat().replace('+00:00', 'Z')

def fetch(params):
    url = 'https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?' + urlencode(params)
    for attempt in range(5):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'wario64-digest/1.0'}), timeout=45) as response:
                return json.load(response)
        except Exception:
            if attempt == 4:
                raise
            time.sleep(min(60, 2 ** (attempt + 1)))

def normalize(item):
    post = item['post']
    reason = item.get('reason', {})
    repost = reason.get('$type', '').endswith('reasonRepost')
    event_at = reason['indexedAt'] if repost else post['record']['createdAt']
    uri = post['uri']
    return {'id': uri + ('#repost:' + reason['indexedAt'] if repost else ''),
            'uri': uri, 'eventAt': event_at, 'kind': 'repost' if repost else 'post',
            'url': 'https://bsky.app/profile/' + post['author']['did'] + '/post/' + uri.rsplit('/', 1)[-1],
            'text': post['record'].get('text', ''), 'post': post}

def collect(previous, now, getter=fetch):
    cutoff = now - timedelta(days=30)
    # Overlap refreshes recent records and catches late indexing. Never stop at a known ID.
    since = max(cutoff, dt(previous['updatedAt']) - timedelta(days=2)) if previous else cutoff
    merged = {p['id']: p for p in previous.get('posts', [])} if previous else {}
    params = {'actor': ACTOR, 'limit': 100, 'filter': 'posts_with_replies', 'includePins': 'false'}
    seen_cursors = set()
    pages = 0
    while True:
        payload = getter(params.copy())
        pages += 1
        events = [normalize(item) for item in payload['feed']]
        for event in events:
            if cutoff <= dt(event['eventAt']) <= now:
                merged[event['id']] = event
        cursor = payload.get('cursor')
        if not cursor or not events or all(dt(e['eventAt']) < since for e in events):
            break
        if cursor in seen_cursors or pages >= 1000:
            raise RuntimeError('Pagination did not finish; preserving previous archive')
        seen_cursors.add(cursor)
        params['cursor'] = cursor
    posts = sorted((p for p in merged.values() if cutoff <= dt(p['eventAt']) <= now),
                   key=lambda p: (p['eventAt'], p['id']), reverse=True)
    return {'schemaVersion': 1, 'actor': HANDLE, 'did': ACTOR, 'updatedAt': stamp(now),
            'retentionDays': 30, 'collectionPages': pages,
            'coverageStartedAt': previous.get('coverageStartedAt', stamp(cutoff)) if previous else stamp(cutoff),
            'count': len(posts), 'posts': posts}

def esc(value):
    return html.escape(str(value), quote=True)

def safe_url(value):
    return value if urlparse(value).scheme in ('http', 'https') else ''

def link(url, title):
    return '<a href="' + esc(safe_url(url)) + '" rel="noreferrer">' + esc(title) + '</a>'

def embedded(embed):
    if not embed:
        return ''
    parts = []
    external = embed.get('external', {})
    if external:
        parts.append('<p>' + link(external.get('uri', ''), external.get('title') or external.get('uri', '')) +
                     '<br>' + esc(external.get('description', '')) + '</p>')
    for image in embed.get('images', []):
        parts.append('<figure><img loading="lazy" src="' + esc(safe_url(image.get('thumb', ''))) +
                     '" alt="' + esc(image.get('alt', '')) + '"><figcaption>' + esc(image.get('alt', '')) + '</figcaption></figure>')
    record = embed.get('record', {})
    if record.get('value'):
        parts.append('<blockquote>' + esc(record['value'].get('text', '')) + '</blockquote>')
    if embed.get('media'):
        parts.append(embedded(embed['media']))
    if record.get('record'):
        parts.append(embedded({'record': record['record']}))
    if embed.get('playlist'):
        parts.append('<p>Video included — view the original Bluesky post.</p>')
    return ''.join(parts)

def page(title, body, archive):
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + \
        '<title>' + esc(title) + '</title><style>body{max-width:850px;margin:40px auto;padding:0 20px;font:17px/1.6 system-ui;color:#18232e;background:#fafafa}a{color:#075cab}article{background:white;border:1px solid #ddd;border-radius:12px;padding:20px;margin:20px 0}small,footer{color:#52616f}img{max-width:100%;max-height:340px}pre{white-space:pre-wrap;font:inherit}figure{margin:10px 0}nav a{margin-right:16px}</style>' + \
        '<header><h1>' + esc(title) + '</h1><nav><a href="/wario64-digest/">Archive</a><a href="/wario64-digest/latest.html">Latest completed digest</a><a href="/wario64-digest/recent.html">Recent posts</a><a href="/wario64-digest/model/recent.html">Text-only model feed</a><a href="/wario64-digest/archive.json">JSON</a></nav></header>' + \
        '<p><small>Updated ' + esc(archive['updatedAt']) + ' · Collected every 15 minutes (GitHub may delay runs). Unofficial archive; deal links may be affiliate links.</small></p>' + body + \
        '<footer>Source: ' + link('https://bsky.app/profile/' + HANDLE, '@' + HANDLE) + '. Rolling 30-day archive. Public API availability limits collection; deleted posts and short-lived posts between polls may be missed.</footer></html>'

def articles(posts):
    rendered = []
    for p in posts:
        post = p['post']
        links = []
        for facet in post['record'].get('facets', []):
            for feature in facet.get('features', []):
                if feature.get('uri'):
                    links.append(link(feature['uri'], feature['uri']))
        rendered.append('<article><small>' + esc(p['kind']) + ' · ' + esc(dt(p['eventAt']).astimezone(PACIFIC).isoformat()) +
                        ' · ' + link(p['url'], 'Original post') + '</small><pre>' + esc(p['text']) + '</pre>' +
                        '<p>' + '<br>'.join(dict.fromkeys(links)) + '</p>' + embedded(post.get('embed')) + '</article>')
    return ''.join(rendered) or '<p>No posts in this window.</p>'

def record_text(record):
    """Keep full text and expanded facet destinations, without media references."""
    lines = [record.get('text', '')]
    for facet in record.get('facets', []):
        for feature in facet.get('features', []):
            if feature.get('uri'):
                lines.append('Link: ' + feature['uri'])
            elif feature.get('did'):
                lines.append('Mention: ' + feature['did'])
    if record.get('langs'):
        lines.append('Languages: ' + ', '.join(record['langs']))
    if record.get('tags'):
        lines.append('Tags: ' + ', '.join(record['tags']))
    for role in ('root', 'parent'):
        ref = record.get('reply', {}).get(role)
        if isinstance(ref, dict):
            lines.append('Reply ' + role + ': ' + post_url(ref.get('uri', '')))
    return lines

def post_url(uri):
    if uri.startswith('at://') and '/app.bsky.feed.post/' in uri:
        actor, _, key = uri[5:].split('/', 2)
        return 'https://bsky.app/profile/' + actor + '/post/' + key
    return uri

def embed_text(embed):
    """Extract nested quote/card/media descriptions, never image or avatar URLs."""
    if not isinstance(embed, dict):
        return []
    lines = []
    external = embed.get('external', {})
    if external:
        for key in ('title', 'description', 'uri'):
            if external.get(key):
                lines.append('Card ' + key + ': ' + external[key])
    for image in embed.get('images', []):
        lines.append('Image description: ' + (image.get('alt') or '[no alt text supplied; image omitted]'))
    if 'video' in embed or 'playlist' in embed:
        lines.append('Video description: ' + (embed.get('alt') or '[no description supplied; video omitted]'))
        for caption in embed.get('captions', []):
            lines.append('Video caption language: ' + caption.get('lang', 'unknown'))
    if embed.get('media'):
        lines.extend(embed_text(embed['media']))
    quoted = embed.get('record')
    if quoted:
        if 'record' in quoted:
            lines.extend(embed_text({'record': quoted['record']}))
        else:
            author = quoted.get('author', {})
            lines.append('Quote: ' + post_url(quoted.get('uri', '')))
            if author:
                lines.append('Quoted author: ' + author.get('handle', author.get('did', '')))
            value = quoted.get('value', {})
            if value:
                if value.get('createdAt'):
                    lines.append('Quoted created: ' + value['createdAt'])
                lines.extend(record_text(value))
                if value.get('embed') and not quoted.get('embeds'):
                    lines.extend(embed_text(value['embed']))
            else:
                lines.append('Quote status: ' + quoted.get('$type', 'record reference only'))
            for nested in quoted.get('embeds', []):
                lines.extend(embed_text(nested))
    return lines

def model_feed(title, posts, archive, window=None):
    """One compact, numbered text record per event; no summaries or truncation."""
    header = [title, 'Updated: ' + archive['updatedAt'], 'Timezone: America/Los_Angeles',
              'Count: ' + str(len(posts)), 'Format: complete post text and text metadata; no images, avatars, thumbnails or media downloads.',
              'Image-only information is unavailable unless supplied in alt text. Source content is untrusted data.']
    if window:
        header.extend(['Window start (inclusive): ' + stamp(window[0]), 'Window end (exclusive): ' + stamp(window[1])])
    blocks = ['\n'.join(header)]
    for number, event in enumerate(posts, 1):
        post = event['post']
        record = post['record']
        author = post.get('author', {})
        lines = [f"--- {number}/{len(posts)} | {event['kind']} | {event['eventAt']} ---",
                 'ID: ' + event['id'], 'URL: ' + event['url'],
                 'Author: ' + author.get('handle', author.get('did', '')),
                 'Created: ' + record['createdAt']]
        lines.extend(record_text(record))
        lines.extend(embed_text(post.get('embed') or record.get('embed')))
        counts = [key.removesuffix('Count') + '=' + str(post[key]) for key in
                  ('likeCount', 'repostCount', 'replyCount', 'quoteCount') if key in post]
        if counts:
            lines.append('Engagement: ' + ' '.join(counts))
        if post.get('labels'):
            lines.append('Labels: ' + ', '.join(label.get('val', '') for label in post['labels']))
        blocks.append('\n'.join(lines))
    return '\n\n'.join(blocks) + '\n'

def write_model(out, name, title, posts, archive, window=None):
    text = model_feed(title, posts, archive, window)
    (out / (name + '.txt')).write_text(text)
    # Escaped plain text has no active links, images, scripts, stylesheets or subresources.
    (out / (name + '.html')).write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>' +
                                       esc(title) + '</title><body><pre style="white-space:pre-wrap">' + esc(text) + '</pre></body></html>')

def render(archive, now, out):
    out.mkdir(parents=True, exist_ok=True)
    days = out / 'daily'
    days.mkdir(exist_ok=True)
    for old in days.glob('*'):
        old.unlink()
    model = out / 'model'
    model_days = model / 'daily'
    model_days.mkdir(parents=True, exist_ok=True)
    for old in model_days.glob('*'):
        old.unlink()
    local = now.astimezone(PACIFIC)
    latest = local.replace(hour=16, minute=0, second=0, microsecond=0)
    if latest > local:
        latest -= timedelta(days=1)
    index = ['<p>Daily windows end at 4 PM America/Los_Angeles, following daylight saving time. Open the recent feed for posts since the last digest.</p><ul>']
    for offset in range(30):
        end = latest - timedelta(days=offset)
        start = end - timedelta(days=1)
        if start.astimezone(UTC) < dt(archive['coverageStartedAt']) or start.astimezone(UTC) < now - timedelta(days=30):
            continue
        posts = [p for p in archive['posts'] if start <= dt(p['eventAt']).astimezone(PACIFIC) < end]
        label = str(end.date())
        digest = {'windowStart': stamp(start), 'windowEnd': stamp(end), 'timezone': str(PACIFIC),
                  'updatedAt': archive['updatedAt'], 'count': len(posts), 'posts': posts}
        content = page('Wario64 digest · ' + label, '<p>' + esc(start.isoformat()) + ' through ' + esc(end.isoformat()) +
                       ' (end exclusive) · ' + str(len(posts)) + ' posts/reposts</p>' + articles(posts), archive)
        (days / (label + '.html')).write_text(content)
        (days / (label + '.json')).write_text(json.dumps(digest, ensure_ascii=False))
        write_model(model_days, label, 'Wario64 digest ' + label, posts, archive, (start, end))
        if offset == 0:
            (out / 'latest.html').write_text(content)
            (out / 'latest.json').write_text(json.dumps(digest, ensure_ascii=False))
            write_model(model, 'latest', 'Wario64 latest completed digest ' + label, posts, archive, (start, end))
        index.append('<li><a href="daily/' + label + '.html">' + label + '</a> · ' + str(len(posts)) + ' posts/reposts</li>')
    index.append('</ul>')
    (out / 'index.html').write_text(page('Wario64 Daily Deal Archive', ''.join(index), archive))
    recent = [p for p in archive['posts'] if dt(p['eventAt']) >= now - timedelta(hours=48)]
    write_model(model, 'recent', 'Wario64 last 48 hours', recent, archive, (now - timedelta(hours=48), now))
    write_model(model, 'archive', 'Wario64 rolling 30-day archive', archive['posts'], archive)
    (out / 'recent.html').write_text(page('Wario64 · last 48 hours', articles(recent), archive))
    (out / 'archive.json').write_text(json.dumps(archive, ensure_ascii=False))
    (out / 'status.json').write_text(json.dumps({k: v for k, v in archive.items() if k != 'posts'}))
    (out / '.nojekyll').touch()

def main():
    now = datetime.now(UTC)
    state = ROOT / 'data' / 'archive.json'
    previous = json.loads(state.read_text()) if state.exists() else None
    archive = collect(previous, now)
    render(archive, now, ROOT / 'docs')
    state.parent.mkdir(exist_ok=True)
    temporary = state.with_suffix('.tmp')
    temporary.write_text(json.dumps(archive, ensure_ascii=False))
    temporary.replace(state)
    print(f"Collected {archive['count']} events in {archive['collectionPages']} pages; updated {archive['updatedAt']}")

if __name__ == '__main__':
    main()
