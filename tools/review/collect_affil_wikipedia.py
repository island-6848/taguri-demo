"""出身・所属の札（dec-member-affil-tag）の外の一覧を、日本語版 Wikipedia の分類から作る。

    python3 tools/review/collect_affil_wikipedia.py collect <控え.json>      # 分類のページを集める（途中から続けられる）
    python3 tools/review/collect_affil_wikipedia.py build <控え.json> cloudflare/scripts/affil_members.json

- API はこの環境の IP では 429 で断られやすいので、普通の分類のページ（HTML）を 3 秒おきに読む〔find-wikipedia-member-categories-1024〕
- STARTO の公式サイトは robots.txt で Claude を断っているので使わない〔find-starto-robots-no-claude-1024〕
- 宝塚歌劇の公式サイトはこの環境から通じない〔find-kageki-unreachable-1024〕
"""
import html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
UA = "taguri-research/0.1 (https://github.com/island-6848/taguri-demo)"
def get(url):
    for i in range(10):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                time.sleep(3)
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404: return ""
            w = int(e.headers.get("retry-after") or 10) + 5 * i
            print("retry", e.code, w, file=sys.stderr, flush=True); time.sleep(w)
        except Exception as e:
            print("retry", e, file=sys.stderr, flush=True); time.sleep(10 * (i + 1))
    raise SystemExit("failed " + url)
def section(page, sid):
    m = re.search(r'<div id="%s".*?(?=<div id="mw-(?:pages|subcategories|category-media)"|<div class="printfooter"|$)' % sid, page, re.S)
    return m.group(0) if m else ""
def titles(block):
    return [html.unescape(t) for t in re.findall(r'<a href="/wiki/[^"]+" title="([^"]+)"', block)]
def fetch_cat(cat):
    pages, subs, url = [], [], "https://ja.wikipedia.org/wiki/" + urllib.parse.quote("Category:" + cat)
    while url:
        page = get(url)
        pages += [t for t in titles(section(page, "mw-pages"))]
        subs += [t.split(":", 1)[1] for t in titles(section(page, "mw-subcategories")) if t.startswith("Category:")]
        nxt = re.search(r'<a href="([^"]+pagefrom=[^"]+)"[^>]*>次のページ', section(page, "mw-pages"))
        url = "https://ja.wikipedia.org" + html.unescape(nxt.group(1)) if nxt else None
    return sorted(set(pages)), sorted(set(subs))
def collect(out):
    state = json.load(open(out)) if os.path.exists(out) else {"cats": {}, "todo": []}
    # todo: [分類, 下へたどる段数, 札の名前]
    if not state["todo"] and not state["cats"]:
        state["todo"] = [[f"宝塚歌劇団{n}期生", 0, "宝塚歌劇団"] for n in range(1, 116)]
        state["todo"] += [[c, 2, "STARTO ENTERTAINMENT"] for c in ("STARTO ENTERTAINMENT所属者", "ジャニーズ事務所の人物", "ジャニーズJr.")]
    while state["todo"]:
        cat, depth, tag = state["todo"].pop(0)
        if cat in state["cats"]:
            continue
        pages, subs = fetch_cat(cat)
        state["cats"][cat] = {"tag": tag, "pages": pages, "subs": subs}
        if depth > 0:
            state["todo"] += [[s, depth - 1, tag] for s in subs if s not in state["cats"]]
        json.dump(state, open(out, "w"), ensure_ascii=False)
        print("ok", cat, len(pages), len(subs), len(state["todo"]), file=sys.stderr, flush=True)


# STARTO は所属者の分類とグループの分類だけを使う。人ごとの分類（「坂本昌行」など、人物別のトピックス）は、
# 配偶者や出た番組も入るので使わない（朝海ひかる・宮沢りえが入っていた）
STARTO_PEOPLE = ("STARTO ENTERTAINMENT所属者", "過去のSTARTO ENTERTAINMENT所属者", "過去のジャニーズ事務所所属者", "ジャニーズJr.", "関西Jr.")
STARTO_GROUPS = ("STARTO ENTERTAINMENTのポップ・グループ", "過去のジャニーズ事務所のポップ・グループ", "過去のSTARTO ENTERTAINMENTのポップ・グループ")
# 人の名前に見える記事名だけ（漢字・かな、2〜8 字）。曲名・番組名の多くはここで落ち、残っても出演欄の名前と合わなければ効かない
NAME = re.compile(r"^[\u4e00-\u9fff\u3005\u3041-\u3096\u30a1-\u30fa\u30fc\u30fb]{2,8}$")


def build(state_path, out_path, retrieved):
    cats = json.load(open(state_path))["cats"]
    groups = set(STARTO_GROUPS)
    for g in STARTO_GROUPS:
        groups.update((cats.get(g) or {}).get("subs") or [])
    use = {"宝塚歌劇団": [c for c in cats if re.fullmatch(r"宝塚歌劇団\d+期生", c)],
           "STARTO ENTERTAINMENT": [c for c in (*STARTO_PEOPLE, *sorted(groups)) if c in cats]}
    clean = lambda t: re.sub(r"\s*\([^)]*\)\s*$", "", t).strip()  # noqa: E731  「瀧川末子 (初代)」→「瀧川末子」
    members = {tag: sorted({n for c in cs for n in map(clean, cats[c]["pages"])
                            if NAME.match(n) and "期生" not in n and "一覧" not in n}) for tag, cs in use.items()}
    json.dump({"about": "出身・所属の札（dec-member-affil-tag）に足す外の一覧。日本語版 Wikipedia の分類のページから、記事名（人の名前）だけを抜き出した。本文は使っていない。",
               "source": f"日本語版 Wikipedia（https://ja.wikipedia.org/）の分類。記事名の抜き出しは {retrieved}。Wikipedia の文章は CC BY-SA 4.0",
               "retrieved": retrieved, "categories": use, "members": members},
              open(out_path, "w"), ensure_ascii=False, indent=1)
    print({k: len(v) for k, v in members.items()})


if __name__ == "__main__":
    if sys.argv[1] == "collect":
        collect(sys.argv[2])
    else:
        build(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else time.strftime("%Y-%m-%d"))
