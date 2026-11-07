"""Check that the static entry point, local module graph and styles share a release URL."""
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[1]

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.version = None
        self.entry = None
        self.styles = []
        self.in_map = False
        self.map_text = ''
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta' and a.get('name') == 'kessel-presentation': self.version = a.get('content')
        if tag == 'link' and a.get('rel') == 'stylesheet': self.styles.append(a['href'])
        if tag == 'script' and a.get('type') == 'module': self.entry = a.get('src')
        if tag == 'script' and a.get('type') == 'importmap': self.in_map = True
    def handle_endtag(self, tag):
        if tag == 'script': self.in_map = False
    def handle_data(self, text):
        if self.in_map: self.map_text += text

def verify():
    p = Page(); p.feed((ROOT / 'index.html').read_text())
    assert p.version, 'Presentation version is missing'
    imports = json.loads(p.map_text)['imports']
    modules = {'./' + str(path.relative_to(ROOT)) for path in (ROOT / 'js').glob('*.js')}
    assert modules <= imports.keys(), 'Unversioned local module in the import graph'
    for source in [imports[m] for m in modules] + p.styles + [p.entry]:
        url = urlsplit(source)
        assert parse_qs(url.query) == {'v': [p.version]}, source
        assert (ROOT / url.path).is_file(), source
    assert p.entry.removeprefix('./') == imports['./js/experience.js'].removeprefix('./'), 'Diagnostic imports must reuse the active app instance'
    print(f'PASS: {len(modules)} local modules, {len(p.styles)} styles and one entry version {p.version}')

if __name__ == '__main__': verify()
