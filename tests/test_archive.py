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
