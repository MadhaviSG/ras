"""Read-only: copy every file under the given ownCloud folders into a local dir (for pilot analysis)."""
import os, sys, xml.etree.ElementTree as ET
from urllib.parse import quote, unquote, urlparse
import requests
DAV = "http://localhost:8092/remote.php/dav/files/theagentcompany/"
AUTH = ("theagentcompany", "theagentcompany")
out = sys.argv[1]
def walk(rel, depth=0):
    r = requests.request("PROPFIND", DAV + quote(rel), headers={"Depth": "1"}, auth=AUTH, timeout=30)
    if r.status_code != 207:
        print(f"  PROPFIND {rel} -> {r.status_code}"); return
    for e in ET.fromstring(r.text).findall(".//{DAV:}response"):
        href = unquote(urlparse(e.find("{DAV:}href").text).path).split("/files/theagentcompany/", 1)[1]
        if href.strip("/") == rel.strip("/"):
            continue
        if href.endswith("/"):
            print(f"  dir  {href}")
            if depth < 6: walk(href, depth + 1)
        else:
            g = requests.get(DAV + quote(href), auth=AUTH, timeout=30)
            p = os.path.join(out, href); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(g.content)
            print(f"  file {href} ({len(g.content)} B)")
for folder in sys.argv[2:]:
    print(f"snapshot {folder} -> {out}")
    walk(folder)
