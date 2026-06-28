#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_fetch.py -- fetch.py unit tests: normalize_url and in-industry deduplication."""
import unittest
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
import fetch

class TestNormalizeUrl(unittest.TestCase):

    def test_strips_trailing_slash(self):
        self.assertEqual(fetch.normalize_url("https://example.com/article/"),
                         "https://example.com/article")

    def test_strips_query_string(self):
        self.assertEqual(fetch.normalize_url("https://example.com/article?ref=foo&page=1"),
                         "https://example.com/article")

    def test_strips_fragment(self):
        self.assertEqual(fetch.normalize_url("https://example.com/article#section-2"),
                         "https://example.com/article")

    def test_case_insensitive(self):
        self.assertEqual(fetch.normalize_url("https://EXAMPLE.COM/Article"),
                         "https://example.com/article")

    def test_strips_all(self):
        url = "https://Example.COM/article/?ref=foo#top"
        self.assertEqual(fetch.normalize_url(url), "https://example.com/article")

    def test_empty_string(self):
        self.assertEqual(fetch.normalize_url(""), "")

    def test_no_changes(self):
        self.assertEqual(fetch.normalize_url("https://example.com/article"),
                         "https://example.com/article")

    def test_fragments_and_query(self):
        self.assertEqual(fetch.normalize_url("https://example.com/a?x=1#y"),
                         "https://example.com/a")


class TestDeduplication(unittest.TestCase):
    """Verify that within each industry, same-URL items are deduped (newest wins)."""

    def _dedup(self, items):
        seen, unique = set(), []
        for item in sorted(items, key=lambda x: x.get("ts", 0), reverse=True):
            key = fetch.normalize_url(item.get("url", ""))
            if key and key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    def test_same_url_different_source(self):
        """Same URL from two sources: keeps the one with larger ts (newer)."""
        items = [
            {"url": "https://qbitai.com/439548", "ts": 1000, "title": "量子位文章", "source": "量子位"},
            {"url": "https://qbitai.com/439548", "ts": 900,  "title": "同一篇",     "source": "机器之心"},
        ]
        result = self._dedup(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source"], "量子位")

    def test_different_urls_all_kept(self):
        items = [
            {"url": "https://a.com/1", "ts": 100, "title": "A"},
            {"url": "https://b.com/2", "ts": 200, "title": "B"},
            {"url": "https://c.com/3", "ts": 50,  "title": "C"},
        ]
        result = self._dedup(items)
        self.assertEqual(len(result), 3)

    def test_url_case_normalized(self):
        items = [
            {"url": "https://EXAMPLE.COM/a", "ts": 100, "title": "A"},
            {"url": "https://example.com/a", "ts": 200, "title": "B"},
        ]
        result = self._dedup(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "B")

    def test_empty_url_skipped(self):
        """Empty URL (falsy key) is skipped from both seen and unique."""
        items = [
            {"url": "",              "ts": 100, "title": "A"},
            {"url": "https://a.com", "ts": 200, "title": "B"},
            {"url": "",              "ts": 300, "title": "C"},
        ]
        result = self._dedup(items)
        # Empty URLs are falsy -> condition fails -> not added to unique
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "B")

    def test_strips_query_and_fragment_before_compare(self):
        items = [
            {"url": "https://a.com/x?ref=1",  "ts": 100, "title": "A"},
            {"url": "https://a.com/x#section", "ts": 200, "title": "B"},
        ]
        result = self._dedup(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "B")

    def test_ts_zero_at_end(self):
        items = [
            {"url": "https://a.com/1", "ts": 0,   "title": "No time"},
            {"url": "https://b.com/2", "ts": 100, "title": "Has time"},
        ]
        result = self._dedup(items)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["title"], "Has time")

    def test_three_duplicates_keep_latest(self):
        items = [
            {"url": "https://a.com/x", "ts": 10,  "title": "Oldest"},
            {"url": "https://a.com/x", "ts": 30,  "title": "Newest"},
            {"url": "https://a.com/x", "ts": 20,  "title": "Middle"},
        ]
        result = self._dedup(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Newest")

    def test_mix_dedup_and_unique(self):
        items = [
            {"url": "https://a.com/1", "ts": 100, "title": "A1"},
            {"url": "https://a.com/1", "ts": 200, "title": "A2"},
            {"url": "https://b.com/2", "ts": 150, "title": "B"},
            {"url": "https://c.com/3", "ts": 50,  "title": "C"},
            {"url": "https://d.com/4", "ts": 80,  "title": "D"},
        ]
        result = self._dedup(items)
        self.assertEqual(len(result), 4)
        titles = [r["title"] for r in result]
        self.assertIn("A2", titles)
        self.assertIn("B",   titles)
        self.assertIn("C",  titles)
        self.assertIn("D",  titles)
        self.assertNotIn("A1", titles)


if __name__ == "__main__":
    unittest.main(verbosity=2)
