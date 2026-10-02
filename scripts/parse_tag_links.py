from pathlib import Path
import re

html_path = Path("data/raw/railway_board/tag_section.html")
content = html_path.read_text(encoding="utf-8", errors="ignore")
print(f"File size: {len(content)} bytes")

from html.parser import HTMLParser

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current_href = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'a':
            attrs_dict = dict(attrs)
            self.current_href = attrs_dict.get('href')
            self.current_text = []

    def handle_data(self, data):
        if self.current_href:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == 'a' and self.current_href:
            text = "".join(self.current_text).strip()
            self.links.append((text, self.current_href))
            self.current_href = None
            self.current_text = []

parser = LinkParser()
parser.feed(content)
print(f"Total links: {len(parser.links)}")
for text, href in parser.links:
    if any(k in text.lower() or k in href.lower() for k in ["table", "tag", "pdf", "train", "glance", "route", "schedule", "view_section", "download"]):
        print(f"[{text}] -> {href}")

