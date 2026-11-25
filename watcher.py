#!/usr/bin/env python3
"""HardverApró figyelő: új hirdetések -> ntfy.sh push értesítés.

Használat:
  NTFY_TOPIC=titkos-topic python watcher.py          # éles futás
  python watcher.py --dry-run                         # nem küld, nem ment
"""
import argparse, html, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")
STATE = os.path.join(HERE, "seen.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
MAX_SEEN = 600


def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "hu"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"  fetch hiba ({i + 1}/{tries}): {e}", file=sys.stderr)
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"Nem sikerült letölteni: {url}")


def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def parse(page):
    items = []
    for chunk in page.split('<li class="media"')[1:]:
        m_id = re.search(r'data-uadid="(\d+)"', chunk)
        m_t = re.search(r'<h1>\s*<a href="([^"]+)">(.*?)</a>', chunk, re.S)
        if not (m_id and m_t):
            continue
        m_p = re.search(r'uad-price">\s*<span[^>]*>(.*?)</span>', chunk, re.S)
        m_c = re.search(r'uad-cities">(.*?)</div>', chunk, re.S)
        price_txt = clean(m_p.group(1)) if m_p else ""
        digits = re.sub(r"\D", "", price_txt)
        items.append({
            "id": m_id.group(1),
            "url": m_t.group(1),
            "title": clean(m_t.group(2)),
            "price_txt": price_txt,
            "price": int(digits) if digits else None,
            "city": clean(m_c.group(1)) if m_c else "",
        })
    return items


def matches(it, s):
    if it["price"] is None:  # "Keresem", "Csere", "Megegyezés" stb.
        return False
    if s.get("min_price") and it["price"] < s["min_price"]:
        return False
    if s.get("max_price") and it["price"] > s["max_price"]:
        return False
    if s.get("include") and not re.search(s["include"], it["title"], re.I):
        return False
    if s.get("exclude") and re.search(s["exclude"], it["title"], re.I):
        return False
    return True


def notify(topic, name, it):
    body = json.dumps({
        "topic": topic,
        "title": f"{name}: {it['price_txt']}",
        "message": f"{it['title']}\n{it['city']}",
        "click": it["url"],
        "tags": ["video_game"],
        "priority": 4,
    }).encode()
    req = urllib.request.Request("https://ntfy.sh/", data=body, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30).read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    topic = os.environ.get("NTFY_TOPIC")
    if not topic and not args.dry_run:
        sys.exit("Hiányzik az NTFY_TOPIC környezeti változó.")

    cfg = json.load(open(CONFIG, encoding="utf-8"))
    state = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
    failed = False

    for s in cfg["searches"]:
        name = s["name"]
        print(f"[{name}]")
        try:
            items = parse(fetch(s["url"]))
        except Exception as e:
            print(f"  HIBA: {e}", file=sys.stderr); failed = True; continue
        if not items:
            print("  HIBA: 0 hirdetés (változhatott az oldal szerkezete?)", file=sys.stderr)
            failed = True; continue

        first_run = name not in state
        seen = state.get(name, [])
        seen_set = set(seen)
        new = [it for it in items if it["id"] not in seen_set]
        hits = [it for it in new if matches(it, s)]
        print(f"  {len(items)} hirdetés, {len(new)} új, {len(hits)} releváns" + (" (első futás: csak mentés)" if first_run else ""))

        for it in reversed(hits):  # régebbi előbb
            print(f"  -> {it['price_txt']} | {it['title']} | {it['url']}")
            if not first_run and not args.dry_run:
                notify(topic, name, it)

        # minden új ID-t eltárolunk (nem releváns is), hogy ne jöjjön elő újra
        state[name] = ([it["id"] for it in new] + seen)[:MAX_SEEN]

    if not args.dry_run:
        json.dump(state, open(STATE, "w", encoding="utf-8"), indent=1)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
