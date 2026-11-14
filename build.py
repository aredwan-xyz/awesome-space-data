#!/usr/bin/env python3
"""Build Awesome Space Data from resources.tsv.

Source (the only file to edit):
    resources.tsv        one resource per line, pipe-delimited

Outputs (regenerated every run, never edit by hand):
    resources.json  resources.csv  index.html  link-status.json
    README.md       (only the parts between the STATS and LIST markers)

Usage:
    python3 build.py                 rebuild and re-check every link (about a minute)
    python3 build.py --no-check      rebuild using the last saved link results
    python3 build.py --report FILE   also write a Markdown list of links that failed

Needs Python 3.8+ and curl. No other dependencies.
"""
import csv
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).parent
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
TODAY = date.today().isoformat()

DOMAINS = {
    "Start here": "Accounts, keys and the main catalogues. Set these up first.",
    "Earth observation": "Satellite imagery, weather, fire, radar, farming, catalogues and the tools to read them.",
    "Canada": "Canadian government and agency sources.",
    "Moon": "Imagery, terrain, temperature and viewers.",
    "Mars": "Imagery, terrain, weather and viewers.",
    "Solar system and ephemeris": "Where things are: positions of bodies and spacecraft, asteroids, planetary archives.",
    "Astrophysics": "Telescope archives, sky viewers and catalogues.",
    "Sun and space weather": "Solar images, storms and aurora feeds.",
    "Human spaceflight and microgravity": "Space biology, microgravity experiments and crew health.",
    "Orbits and satellites": "Orbit data, launch schedules and satellite databases.",
    "Mission engineering and software": "Mission-control and flight software, handbooks and standards.",
    "Missions and history": "Past spacecraft and what they did.",
    "Media, 3D and visualization": "Images, video, 3D models, textures and finished visualizations.",
    "Web and data libraries": "Mapping, 3D, charts and sound in the browser.",
    "Learning": "Courses, primers and classroom material.",
    "Ventures and industry": "Funding, licensing, regulation, news and market reports.",
}
FIELDS = ["id", "domain", "kind", "name", "url", "description", "access", "terms", "link_ok", "http_status", "last_checked"]


def anchor(title):
    return re.sub(r"[^a-z0-9 -]", "", title.lower()).replace(" ", "-")


def load():
    rows, seen = [], {}
    for n, line in enumerate((HERE / "resources.tsv").read_text().splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 7:
            sys.exit(f"resources.tsv line {n}: expected 7 fields separated by |, got {len(parts)}")
        domain, kind, access, terms, name, url, desc = parts
        if domain not in DOMAINS:
            sys.exit(f"resources.tsv line {n}: unknown domain '{domain}'")
        if not re.match(r"https?://", url):
            sys.exit(f"resources.tsv line {n}: url must start with http:// or https://")
        if not (kind and access and name and desc):
            sys.exit(f"resources.tsv line {n}: kind, access, name and description are required")
        key = re.sub(r"/+$", "", url.lower().replace("http://", "https://").replace("https://www.", "https://"))
        if key in seen:
            sys.exit(f"resources.tsv line {n}: duplicate of line {seen[key]} ({url})")
        seen[key] = n
        rows.append({"domain": domain, "kind": kind, "access": access, "terms": terms, "name": name, "url": url, "description": desc})
    order = list(DOMAINS)
    rows.sort(key=lambda r: order.index(r["domain"]))  # stable: keeps file order inside a domain
    return rows


def check(url):
    try:
        code = subprocess.run(["curl", "-sL", "--max-time", "25", "-A", UA, "-o", "/dev/null", "-w", "%{http_code}", url],
                              capture_output=True, text=True, timeout=40).stdout.strip() or "000"
    except subprocess.TimeoutExpired:
        code = "000"
    return url, code


def verdict(code):
    if code.startswith(("2", "3")):
        return "yes"
    if code in ("401", "403", "405", "429"):
        return "refused checker"
    return "no response"


def badge(label, message, colour):
    return f"![{label}](https://img.shields.io/badge/{quote(label)}-{quote(str(message)).replace('-', '--')}-{colour})"


def readme_list(rows):
    out = ["## Contents", ""]
    for d in DOMAINS:
        n = sum(1 for r in rows if r["domain"] == d)
        if n:
            out.append(f"- [{d}](#{anchor(d)}) ({n})")
    for d, blurb in DOMAINS.items():
        group = [r for r in rows if r["domain"] == d]
        if not group:
            continue
        out += ["", f"## {d}", "", f"_{blurb}_", ""]
        for r in group:
            flag = "" if r["link_ok"] in ("yes", "refused checker") else " ⚠️"
            terms = f" Reuse: {r['terms']}." if r["terms"] else ""
            out.append(f"- [{r['name']}]({r['url']}){flag} — {r['description']} `{r['kind']}` `{r['access']}`{terms}")
    return "\n".join(out)


def replace_between(text, tag, body):
    pattern = re.compile(rf"(<!-- {tag}:START -->).*?(<!-- {tag}:END -->)", re.S)
    if not pattern.search(text):
        sys.exit(f"README.md is missing the {tag} markers")
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(2)}", text)


def main():
    rows = load()
    cache_path = HERE / "link-status.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    if "--no-check" not in sys.argv:
        with ThreadPoolExecutor(max_workers=12) as ex:
            for url, code in ex.map(check, sorted({r["url"] for r in rows})):
                cache[url] = {"code": code, "checked": TODAY}
        # Sites that throttle parallel requests can fail the first pass. Retry failures one at a time.
        for attempt in range(2):
            failed = [u for u in sorted({r["url"] for r in rows}) if verdict(cache[u]["code"]) == "no response"]
            if not failed:
                break
            time.sleep(5)
            for url in failed:
                cache[url] = {"code": check(url)[1], "checked": TODAY}
                time.sleep(1)
    cache = {r["url"]: cache[r["url"]] for r in rows if r["url"] in cache}  # drop entries for removed resources
    cache_path.write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n")

    for i, r in enumerate(rows, 1):
        st = cache.get(r["url"], {})
        r.update(id=i, http_status=st.get("code", ""), link_ok=verdict(st["code"]) if st else "not checked",
                 last_checked=st.get("checked", ""))
    rows = [{k: r[k] for k in FIELDS} for r in rows]
    checked = max((r["last_checked"] for r in rows if r["last_checked"]), default="never")
    ok = sum(1 for r in rows if r["link_ok"] == "yes")
    refused = sum(1 for r in rows if r["link_ok"] == "refused checker")
    bad = [r for r in rows if r["link_ok"] not in ("yes", "refused checker")]
    used = [d for d in DOMAINS if any(r["domain"] == d for r in rows)]

    meta = {"count": len(rows), "domains": used, "links_checked": checked, "links_responding": ok}
    (HERE / "resources.json").write_text(json.dumps({"meta": meta, "resources": rows}, indent=1, ensure_ascii=False) + "\n")
    with open(HERE / "resources.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    page = (HERE / "template.html").read_text()
    page = page.replace("/*DATA*/", json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")).replace("{{CHECKED}}", checked)
    (HERE / "index.html").write_text(page)

    stats = " ".join([
        badge("resources", len(rows), "1d4ed8"), badge("domains", len(used), "1d4ed8"),
        badge("links responding", f"{ok}/{len(rows)}", "15803d"), badge("last checked", checked, "555555"),
    ])
    readme = (HERE / "README.md").read_text()
    readme = replace_between(readme, "STATS", stats)
    readme = replace_between(readme, "LIST", readme_list(rows))
    (HERE / "README.md").write_text(readme)

    if "--report" in sys.argv:
        lines = [f"Link check on {checked}: {ok} of {len(rows)} links responded, {refused} refused the automated check, {len(bad)} did not respond.", ""]
        if bad:
            lines += ["| Resource | Status | Link |", "|---|---|---|"] + [f"| {r['name']} | {r['http_status'] or 'none'} | {r['url']} |" for r in bad]
        Path(sys.argv[sys.argv.index("--report") + 1]).write_text("\n".join(lines) + "\n")

    print(f"{len(rows)} resources in {len(used)} domains")
    print(f"{ok} links respond, {refused} refused the checker, {len(bad)} did not respond")
    for r in rows:
        if r["link_ok"] != "yes":
            print(f"  {r['http_status'] or '---'}  {r['name'][:50]}  {r['url']}")


if __name__ == "__main__":
    main()
