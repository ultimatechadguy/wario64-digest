import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import archive as a

def item(number, when, repost=False):
    p = {'post': {'uri': 'at://did:plc:test/app.bsky.feed.post/' + str(number),
                 'author': {'did': 'did:plc:test'},
                 'record': {'createdAt': a.stamp(when), 'text': '<script>unsafe</script>'}}}
    if repost:
        p['reason'] = {'$type': 'app.bsky.feed.defs#reasonRepost', 'indexedAt': a.stamp(when)}
    return p

class ArchiveTests(unittest.TestCase):
    def test_model_feed_preserves_text_quotes_links_and_alt_without_media(self):
        now = datetime.now(a.UTC)
        source = item(1, now)
        source['post']['author']['avatar'] = 'https://cdn.example/avatar.jpg'
        source['post']['record']['text'] = 'Full text ' * 1000
        source['post']['record']['facets'] = [{'features': [{'uri': 'https://store.example/deal'}]}]
        source['post']['record']['reply'] = {'$type': 'app.bsky.feed.post#replyRef',
            'parent': {'uri': 'at://did:plc:parent/app.bsky.feed.post/parent'}}
        source['post']['embed'] = {
            'media': {'images': [{'alt': 'Coupon code SAVE20', 'thumb': 'https://cdn.example/thumb.jpg',
                                  'fullsize': 'https://cdn.example/full.jpg'}]},
            'record': {'record': {'uri': 'at://did:plc:quote/app.bsky.feed.post/abc',
                'author': {'handle': 'quoted.example', 'avatar': 'https://cdn.example/quote.jpg'},
                'value': {'text': 'Quoted offer text', 'createdAt': a.stamp(now)},
                'embeds': [{'external': {'uri': 'https://store.example/quoted', 'title': 'Offer title',
                                        'description': 'Offer conditions', 'thumb': 'https://cdn.example/card.jpg'}}]}}}
        event = a.normalize(source)
        text = a.model_feed('test', [event], {'updatedAt': a.stamp(now)})
        for value in (source['post']['record']['text'], 'https://store.example/deal', 'Coupon code SAVE20',
                      'Quoted offer text', 'Offer title', 'Offer conditions', 'https://store.example/quoted',
                      'https://bsky.app/profile/did:plc:quote/post/abc',
                      'Reply parent: https://bsky.app/profile/did:plc:parent/post/parent'):
            self.assertIn(value, text)
        self.assertNotIn('cdn.example', text)
        self.assertEqual(text.count('--- 1/1 |'), 1)
        with tempfile.TemporaryDirectory() as tmp:
            a.write_model(Path(tmp), 'test', 'test', [event], {'updatedAt': a.stamp(now)})
            output = (Path(tmp) / 'test.html').read_text()
            for forbidden in ('<img', '<video', '<script', '<iframe', 'src=', 'cdn.example'):
                self.assertNotIn(forbidden, output)

    def test_pagination_dedup_and_pruning(self):
        now = datetime(2026, 10, 22, 0, tzinfo=a.UTC)
        recent = item(1, now - timedelta(hours=1))
        old = item(3, now - timedelta(days=31))
        previous = {'updatedAt': a.stamp(now - timedelta(minutes=15)),
                    'posts': [a.normalize(recent), a.normalize(old)]}
        calls = []
        def getter(params):
            calls.append(params)
            if 'cursor' not in params:
                return {'feed': [recent], 'cursor': 'next'}
            return {'feed': [recent, item(2, now - timedelta(hours=2)), old]}
        result = a.collect(previous, now, getter)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]['cursor'], 'next')
        self.assertEqual(result['count'], 2)

    def test_repeated_cursor_fails(self):
        now = datetime.now(a.UTC)
        with self.assertRaises(RuntimeError):
            a.collect(None, now, lambda _: {'feed': [item(1, now)], 'cursor': 'same'})

    def test_dst_window_and_html_escaping(self):
        now = datetime(2026, 11, 2, 1, tzinfo=a.UTC)
        end = now.astimezone(a.PACIFIC).replace(hour=16, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=1)
        self.assertEqual((end.astimezone(a.UTC) - start.astimezone(a.UTC)).total_seconds(), 25 * 3600)
        record = a.normalize(item(1, end.astimezone(a.UTC) - timedelta(minutes=1)))
        archive = {'updatedAt': a.stamp(now), 'coverageStartedAt': a.stamp(now - timedelta(days=30)), 'posts': [record]}
        with tempfile.TemporaryDirectory() as tmp:
            a.render(archive, now, Path(tmp))
            output = (Path(tmp) / 'latest.html').read_text()
            self.assertIn('&lt;script&gt;', output)
            self.assertNotIn('<script>', output)
            self.assertIn('1 posts/reposts', output)

if __name__ == '__main__':
    unittest.main()
