"""Cross-entry contracts: no section can quietly lose the shared application UI."""
from html.parser import HTMLParser
from pathlib import Path
import unittest
from urllib.parse import urlsplit

from scripts.curation.verify_published_register import RENDERER_ASSETS

SITE = Path(__file__).resolve().parents[1] / 'site'
DESTINATIONS = ['index.html', 'database.html', 'stats.html', 'method.html', 'model.html', 'curate.html']
PRIVATE = {'curate.html', 'enrichment.html', 'review-v2.html'}
PUBLIC_ROOT = 'https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/'


class Entry(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.styles, self.navigation, self.links = [], [], []
        self.in_navigation = False
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.styles.append(attrs['href'])
        if tag == 'nav':
            self.in_navigation = attrs.get('aria-label') == 'Navigazione principale'
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
            if self.in_navigation:
                self.navigation.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'nav':
            self.in_navigation = False


class SharedApplicationDesignTests(unittest.TestCase):
    def test_every_entry_loads_the_same_versioned_contract_last(self):
        for path in SITE.glob('*.html'):
            with self.subTest(page=path.name):
                styles = Entry(path).styles
                contract = [urlsplit(s) for s in styles if urlsplit(s).path.endswith('/application.css')]
                self.assertEqual(len(contract), 1)
                self.assertEqual(contract[0], urlsplit(styles[-1]))
                self.assertEqual(contract[0].query, 'v=sections-20260929')

    def test_navigation_is_complete_ordered_and_identifies_the_section(self):
        for path in SITE.glob('*.html'):
            with self.subTest(page=path.name):
                links = Entry(path).navigation
                self.assertEqual([urlsplit(a['href']).path.rsplit('/', 1)[-1] for a in links], DESTINATIONS)
                current = [a for a in links if a.get('aria-current') == 'page']
                expected = 'curate.html' if path.name in PRIVATE else path.name
                self.assertEqual(len(current), int(expected in DESTINATIONS))
                if current:
                    self.assertTrue(current[0]['href'].endswith(expected))
                if path.name in PRIVATE:
                    for link in links[:-1]:
                        self.assertTrue(link['href'].startswith(PUBLIC_ROOT))

    def test_deployment_receipt_covers_every_entry_and_its_static_styles(self):
        for path in SITE.glob('*.html'):
            with self.subTest(page=path.name):
                self.assertIn(path.name, RENDERER_ASSETS)
                for href in Entry(path).styles:
                    self.assertIn(urlsplit(href).path.rsplit('/', 1)[-1], RENDERER_ASSETS)

    def test_nested_error_routes_keep_working_styles_and_recovery_links(self):
        page = Entry(SITE / '404.html')
        for href in page.styles + page.links:
            if not href.startswith('#'):
                self.assertTrue(href.startswith(PUBLIC_ROOT), href)

    def test_component_styles_cannot_redefine_the_application_palette(self):
        for name in ('classic-site.css', 'model.css', 'curator-reading.css', 'database.css', 'method.css'):
            with self.subTest(name=name):
                self.assertNotRegex((SITE / name).read_text(), r'--classic-[\w-]+\s*:')


if __name__ == '__main__':
    unittest.main()
