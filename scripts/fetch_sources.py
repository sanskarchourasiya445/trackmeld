import urllib.request
import re
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://indianrailways.gov.in/railwayboard/view_section.jsp?lang=0&id=0,1,304,366,537,2960'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        print(f"Length of page: {len(html)}")
        links = re.findall(r'href=["\']([^"\']+\.pdf)["\']', html, re.IGNORECASE)
        print(f"PDF links found: {len(links)}")
        for l in links[:20]:
            print("PDF:", l)
        links_all = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.IGNORECASE)
        print(f"Total links: {len(links_all)}")
        for href, text in links_all[:30]:
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            if clean_text:
                print(f"{clean_text} -> {href}")
except Exception as e:
    print("Error:", e)
