#!/usr/bin/env python3
"""公演ページの本文から、あらすじと内容の要素を LLM に抜き出させる（網 C・V6c）。

## なぜ担い手を変えたのか

規則による切り出しは**実質 24%** しか本物のあらすじを取れなかった
（[検証 020](../../docs/verification/020-synopsis-extraction-quality.md)）。
「見出しで探し、無ければ最長の段落」というフォールバックが、劇団紹介・他公演の一覧・
著作権表示・テンプレートのダミー文（Lorem ipsum）・クチコミのタグを拾っていた。
**劇団紹介とあらすじを文字数や位置では区別できない**と実証できたので、
ここは LLM を部品として使う正当な場所である（境界の決まった変換で、正解データで採点できる）。

## 本文をそのまま渡さない ── ナビがあらすじを押し出す

実データを見ると、公演ページの先頭 1,500 字はほぼ全部ナビゲーション（メニュー・劇場の一覧・
言語切替）である。先頭から切って渡すと、**あらすじが 1 文字も入らないまま LLM に渡ることになる。**
そこで **20 字未満の行を落として重複行を除く**前処理を入れる。実測では 5,500 字のページが
1,159 字に縮み、あらすじは残った。

## 抽出は 1 回で確定させる

企画書 5 章のとおり、**同じ公演を週によって違う要素で数えると、当たり率も持ち上がりも週ごとに動く。**
そこで結果は `data/credits/themes.jsonl` に確定させ、**モデルとプロンプトの版を行に記録する。**
版を上げるときは `--refresh` で全件を引き直す（一部だけ新しくしない）。

## LLM の呼び出し口

**Gemini API を専用の鍵で呼ぶ**（`tools/llm_gemini.py`）。以前は `claude` CLI を
サブプロセスとして呼んでいたが、対話用セッションと同じ枠・同じログイン状態に
バッチ処理の認証まで乗せるのはコストとセキュリティの両面でまずいという指摘
（起案者・2026-08-27）を受けて切り離した。入出力の型（JSON 配列）を固定して
いるので、担い手を替えても呼び出し側は変わらない。

    python3 tools/credits/extract_theme_llm.py --side candidate --limit 40
    python3 tools/credits/extract_theme_llm.py --side both
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "tools" / "review"))
sys.path.insert(0, str(ROOT / "tools"))
from fetch_official_credits import CACHE, get, to_text      # noqa: E402
import hand_themes as HT                                    # noqa: E402
import llm_gemini as LLM                                    # noqa: E402

CAND = ROOT / "data" / "review" / "candidates.jsonl"
CORICH = ROOT / "data" / "credits" / "pages"      # CoRich の公演ページ（取得済み）
CREDITS = ROOT / "data" / "credits" / "credits.jsonl"
OUT = ROOT / "data" / "credits" / "themes.jsonl"

PROMPT_VERSION = "g2"
MODEL = LLM.MODEL

PROMPT_C2 = """あなたは演劇の公演ページの本文から、あらすじと内容の要素を抜き出す部品である。
入力は複数の公演で、それぞれ「### id: <id>」の行で始まり、次の「###」までがその公演の本文である。

各公演について次の 2 つを判定する。

1. synopsis ── 本文の中に、**その公演の物語・内容の説明**があれば、その部分を 60〜300 字で抜き出す。
   - 本文にある表現をそのまま使う。要約や創作をしない。
   - 次のものはあらすじではない。空文字を返す。
     劇団・劇場・施設の紹介／他公演の一覧／日程・料金・チケット・アクセスの案内／著作権表示／
     テンプレートのダミー文（Lorem ipsum）／クチコミ・SNS の投稿／出演者の挨拶やブログ記事／
     受賞歴や公演の宣伝文だけのもの。
   - 判断に迷ったら空文字にする。**取れなかったことは測定値なので、埋めなくてよい。**

2. elements ── 内容の要素を最大 5 つ。各要素は {"kind": "...", "word": "..."} の形にする。
   - kind は「題材」「舞台設定」「トーン」「原作」のいずれか。
   - word は 1〜4 語の**一般名詞**にする（例: 家族、法廷、戦争、題材3、恋愛、会話劇、群像劇、
     ミステリー、時代物）。人名・作品名・地名などの固有名詞は word にしない。
   - ただし kind が「原作」のときだけ固有名詞でよい（例: 作品3、シェイクスピア、太宰治）。
   - 「感動」「衝撃」「話題」「必見」「圧巻」のような宣伝の語は出さない。
   - **synopsis が空なら elements も空にする**（本文が無いのに要素を作らない）。

出力は JSON 配列だけを返す。前後に説明や```を書かない。

[{"id":"<id>","synopsis":"...","elements":[{"kind":"題材","word":"..."}]}]

入力:

"""

def _sub(text: str, old: str, new: str) -> str:
    """**当たらなかった置換を黙って見逃さない。** 版の差分を replace で書いているので、
    文面を触ったときに置換が空振りすると、版だけ上がって中身が前の版のままになる。"""
    if old not in text:
        raise AssertionError(f"プロンプトの置換が当たらない: {old[:32]}")
    return text.replace(old, new, 1)


# **c2 の文面は書き換えない。** 検証 038 の正解データに対する前後の比較が、
# 同じ文面で測り直せなくなる。新しい版は差分だけを書く。
#
# c3 ── **題名を渡し、別公演の物語を取らせない。**
# c2 は id と本文だけを渡していたので、1 ページに複数の公演が載っているとき
# **モデルにはどれが当該公演か判断する材料が無かった。** 検証 038 の段 2 で、
# 別公演の要素が学習に入った例が 3 件出ている（『流浪樹』に『さよなら挽歌』の
# 妊活・闇バイト、『俺たちのBANG!!!』に『1993-The Bang Bang Club-』の報道・戦争）。
# 検証 023 は「LLM に渡す指示に別公演の混入を書く」と決めていたが、実装に入っていなかった。
PROMPT_C3 = _sub(
    PROMPT_C2,
    "次の「###」までがその公演の本文である。",
    "次の行が「題名: <公演の題名>」、その次から「###」までがその公演の本文である。",
)
PROMPT_C3 = _sub(
    PROMPT_C3,
    "1. synopsis ── 本文の中に、**その公演の物語・内容の説明**があれば、",
    "1. synopsis ── 本文の中に、**題名で示した公演の物語・内容の説明**があれば、",
)
PROMPT_C3 = _sub(
    PROMPT_C3,
    "   - 判断に迷ったら空文字にする。",
    "   - **本文には別の公演の情報が混ざっていることがある。** 団体のサイトは過去公演と次回公演を\n"
    "     同じページに並べ、劇場のサイトは複数の公演を並べる。1 ページに複数の演目が載ることもある。\n"
    "     **題名の公演と結び付かない物語しか無ければ、空文字を返す。**\n"
    "   - 判断に迷ったら空文字にする。",
)

# c4 ── **「迷ったら空」の言い方を直す。**
# 検証 038 の段 3 で、取れなかった 25 件のうち 7 件は**本文にその公演の物語があるのに空**だった
# （『A・NUMBER』の「クローン技術が進み…父の対話から始まる」は渡した本文の中にある）。
# c2 の「判断に迷ったら空文字」「埋めなくてよい」は**創作を止めるための指示**だったが、
# **あるものを見送る側にも効いていた疑いがある。** 創作の禁止は残し、見送りだけを止める。
PROMPT_C4 = _sub(
    PROMPT_C3,
    "   - 判断に迷ったら空文字にする。**取れなかったことは測定値なので、埋めなくてよい。**",
    "   - **その公演の物語が本文にあるなら、短くても、宣伝文と地続きでも、その部分を取る。**\n"
    "     空文字にするのは、**物語がどこにも書かれていないか、別公演のものしか無いとき**だけである。\n"
    "     **本文に無いことを創作して埋めてはいけないが、本文にあるものを見送る必要もない。**",
)

# c5 ── **要素の上限を 5 から 8 に上げる。**
# **5 の根拠は記録に無い。** このスクリプトの初版から入っていた数字で、コミットにも検証にも
# 理由が書かれていない。**上限は実際に効いている** ── あらすじが取れた 714 行のうち
# 230 行（32%）がちょうど 5 個で、切られた可能性がある。網 C の公演の強さは
# 「寄与が正の上位 3 個の和」なので 6 個目以降が順位に直接効くのは上の 3 個を上回るときだけだが、
# **申告した題材との照合（C-申告）と持ち上がりの母数（C-推定）には全部が効く。**
PROMPT_C5 = _sub(
    PROMPT_C4,
    "2. elements ── 内容の要素を最大 5 つ。",
    "2. elements ── 内容の要素を最大 8 つ。",
)

# c6 ── **あらすじが空でも、内容が書かれていれば要素は取る。**
# 検証 048 の段 1 ── 取れなかった候補 344 件を読み直すと、**本文に物語があるのに空を返した行は
# 0/40 件**で、取りこぼしではなかった。内訳は「物語がどこにも無い」45%、
# **「そもそも筋書きを持たない催し」（フェス・落語会・ダンス・レビュー）42%**、
# **「物語ではないが内容の説明はある」12%** である。後ろの 2 つは**本文に題材が書かれている**
# （『ゾンビフェス』の「ゾンビ」、『エリザベート』の「ミュージカル」）のに、
# c2 から続く「synopsis が空なら elements も空にする」がまとめて捨てていた。
# **創作の禁止は残す** ── 空にするのは、本文に内容が何も書かれていないときだけである。
PROMPT_C6 = _sub(
    PROMPT_C5,
    "   - **synopsis が空なら elements も空にする**（本文が無いのに要素を作らない）。",
    "   - **synopsis が空でも、本文にその公演の内容が書かれていれば elements は取る。**\n"
    "     筋書きを持たない催し（フェス・オムニバス・落語会・ダンス・レビュー）や、\n"
    "     宣伝文・企画意図しか無いページでも、**本文から言える題材・舞台設定・トーンを書く。**\n"
    "   - elements を空にするのは、**本文にその公演の内容が何も書かれていないとき**"
    "（日程・料金・出演者・団体の案内しか無い）と、**別公演の内容しか無いとき**だけである。\n"
    "   - **本文に無いことを創作して埋めてはいけない。** 題名から連想しただけの語を書かない。",
)

# g1 ── **担い手を Gemini に替えたことで悪化した「空を返す」判断を立て直す。**
# 検証 050（V78）── c2〜c4 の文面のまま呼び出す LLM だけを claude CLI から Gemini に
# 替えて測り直すと、「別公演を掴んだ→空を保った」100%→14〜33%、「空が正しい→空」
# 100%→61〜67% に落ちた（「取りこぼし→取れた」はほぼ横ばい）。**書いた内容は
# `verbatim()` を通る ── 本文のどこかに実在する文字列ではある。** 起案者の問い
# 「『取らない』側の判断を claude CLI レベルに上げることはできないか」を受けて、
# **c6 に「書く前に、これは本当に題名の公演の物語だと言えるか」を自問させる一段と、
# 具体例を足す。** c2〜c6 の文面は変えない（測り直せなくなる）。効果は同じ測り方
# （検証 042／050 の道具・標本）で確かめてから採否を決める。
PROMPT_G1 = _sub(
    PROMPT_C6,
    "     **題名の公演と結び付かない物語しか無ければ、空文字を返す。**",
    "     **題名の公演と結び付かない物語しか無ければ、空文字を返す。**\n"
    "   - **synopsis を書く前に自問する ── 「この一段落が《題名》自身の物語だという根拠"
    "（登場人物・出来事が題名の内容と対応する）を、本文の中で示せるか」。** 示せなければ、"
    "どれほど物語らしく読めても使わない。\n"
    "   - 例: 題名が「A」で、本文が劇団・企画の紹介として代表作「B」のあらすじを載せている場合、"
    "**B のあらすじを A の synopsis にしてはいけない**（空文字にする）。\n"
    "   - **空文字は失敗ではない。** 本文の大半は、その公演の物語そのものを書いていない"
    "（日程・出演者・団体紹介・他公演の話）。空文字を避けようとして、根拠の弱い一致を拾わない。",
)

# g2 ── **人物間の具体的な関係を、曖昧な語に丸めずに拾う。**
# 起案者の指摘（2026-08-28）「他のユーザーが出演者はさておきあらすじだけで興味ありに
# するような使い方をしていたら？」を受け、自分の当たりやすさ（AUC・V79）とは別に、
# **本文と抜き出した語を 1 件ずつ突き合わせて確かめた。** 3 件で具体的な取りこぼしが
# 見つかった ──「ヴィンセント・イン・ブリクストン」は本文に「ユージェニーに惹かれて」と
# あるのに `人間関係` という曖昧な語に丸めていた（`恋愛` を出していない）。
# 「ダブル・トラブル」は本文に「仕事に恋に奔走する」と両方書いてあるのに `仕事` だけを
# 拾い `恋愛` を落としていた。「A・NUMBER」は本文の核心（医療機関が依頼者に黙って
# 複数のクローンを作っていた）である `生命倫理`／`医療機関` を一切拾っていなかった。
# **どれも本文に明記されている内容で、創作の余地は無い。** 具体的な語を優先させる一段を足す。
PROMPT_G2 = _sub(
    PROMPT_C6,
    "   - 「感動」「衝撃」「話題」「必見」「圧巻」のような宣伝の語は出さない。",
    "   - **人物どうしの関係や葛藤が本文に具体的に書かれているときは、"
    "「人間関係」のような曖昧な語に丸めず、恋愛・友情・確執・対立・裏切りなど"
    "具体的な語にする。** 例:「〇〇に惹かれて」「恋に奔走する」とあれば `恋愛` を、"
    "「騙されていた」とあれば `裏切り` を出す。\n"
    "   - **本文に書かれている倫理的な問題や社会的な論点（生命倫理・差別・貧困など）も、"
    "登場人物の名前や職業だけでなく、その問題自体を語として出す。**\n"
    "   - 「感動」「衝撃」「話題」「必見」「圧巻」のような宣伝の語は出さない。",
)

PROMPTS = {"c2": PROMPT_C2, "c3": PROMPT_C3, "c4": PROMPT_C4,
           "c5": PROMPT_C5, "c6": PROMPT_C6, "g1": PROMPT_G1, "g2": PROMPT_G2}

# **要素の上限は版ごとに違う。** 版だけ上げてコード側の切り詰めが 5 のままだと、
# 指示は 8 個を許しているのに書き出しで 5 個に落ちる（版の比較が成立しない）。
MAX_ELEMENTS = {"c2": 5, "c3": 5, "c4": 5, "c5": 8, "c6": 8, "g1": 8, "g2": 8}


_lock = threading.Lock()


def verbatim(syn: str, src: str) -> bool:
    """**抽出したあらすじが、渡した本文に実在するかを検査する。**

    規則の失敗は目で見つけられた（Lorem ipsum・劇団紹介）。**LLM の失敗は目で見つけにくい。**
    実例 ──「ゴースト」の公演ページには宣伝文しか無いのに、抽出されたのは
    映画『ゴースト/ニューヨークの幻』の筋書きそのものだった。**モデルが自分の知識で書いている。**
    企画書 3 章の「理由は事実だけで書き、出典を必ず付ける」に触るので、
    **本文に実在しない抽出は落とす。**

    判定は 12 字の窓を等間隔に 5 つ取り、**3 つ以上が本文にあること**とする。
    LLM が空白や記号を落とすことがあるので、比較は英数と仮名・漢字だけに正規化して行う。
    """
    def only(s: str) -> str:
        return re.sub(r"[^0-9A-Za-z\u3040-\u30ff\u4e00-\u9fff]", "", s)
    a, b = only(syn), only(src)
    if len(a) < 24 or not b:
        return False
    win, hit = 12, 0
    spots = [int(i * (len(a) - win) / 4) for i in range(5)]
    for s in spots:
        if a[s:s + win] in b:
            hit += 1
    return hit >= 3


def prep(html: str, limit: int = 5000) -> str:
    """ナビを落として本文だけにする。**20 字未満の行と重複行を除く。**"""
    t = unicodedata.normalize("NFKC", to_text(html))
    seen: set[str] = set()
    out: list[str] = []
    for line in t.split("\n"):
        s = re.sub(r"\s+", " ", line).strip()
        if len(s) < 20 or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return "\n".join(out)[:limit]


def url_of(field: str) -> str:
    m = re.search(r'https?://[^\s"<>）)]+', field or "")
    return m.group(0).rstrip("。、") if m else ""



# **クチコミ・自動表示ツイートは、LLM に見せる前に構造で切り落とす。** プロンプトの指示
# （「クチコミ・SNS の投稿は synopsis にしない」）だけでは Gemini が時々拾ってしまう
# （検証 050 追記 2 ── DREAM BOYS は自動表示ツイートの一文、作品1 −Eternal− は
# ユーザーの感想がそのまま synopsis に混ざった）。CoRich のページはどちらも固定の
# コンテナで区切られている ── クチコミは `id="areaKuchikomi"`（1,758 ページで確認、
# 全件が次の `<div class="area">` まで境界を持つ）、自動表示ツイートは `id="areaTweet"`
# （29 ページで確認、全件がページ内で最後の area ブロックである）。**ここを削れば、
# 「除外して」と頼む対象がそもそも本文に存在しなくなる。**
_KUCHIKOMI_RE = re.compile(r'<div class="area" id="areaKuchikomi">.*?(?=<div class="area")', re.S)
_TWEET_RE = re.compile(r'<div class="area" id="areaTweet">.*', re.S)


def strip_reviews(html: str) -> str:
    html = _KUCHIKOMI_RE.sub("", html)
    html = _TWEET_RE.sub("", html)
    return html


def corich_text(stage_id: str, limit: int = 2500) -> str:
    """**CoRich の公演ページも材料にする。**

    検証 020 は「CoRich にあらすじ欄が無い（100 字以上の説明は 17%）」と測って公式サイトだけを
    見に行っていたが、実際のページには**その公演のあらすじが本文として載っている**
    （「ガリレイの生涯」で確認 ──「カトリック教会の言論から逃れたガリレイに…」）。
    しかも**候補の取得で既にキャッシュしてあるので、新しい取得は 1 回も発生しない。**
    公式サイトの URL 欄が空の公演（ガリレイの生涯がこれ）でも、ここから材料が取れる。
    """
    key = CORICH / f"https___stage_corich_jp_stage_{stage_id}.html"
    if not key.exists():
        return ""
    return prep(strip_reviews(key.read_text(encoding="utf-8")), limit)


def cached(url: str) -> str:
    key = CACHE / (re.sub(r"[^A-Za-z0-9]", "_", url)[-120:] + ".html")
    return key.read_text(encoding="utf-8") if key.exists() else ""


def targets(side: str, fetch: bool) -> list[dict]:
    """{id, title, url, text} を返す。**キャッシュが無ければ取得する（1 リクエスト／秒）。**"""
    rows: list[dict] = []
    if side == "candidate":
        for c in (json.loads(l) for l in CAND.read_text(encoding="utf-8").split("\n") if l.strip()):
            # **終わった公演のあらすじは取らない。** `fetch_candidates.py --keep-days` が
            # 手で足す欄の候補として残している行で、**推薦のどの束にも入らない**
            # （`recommend2.py` が `end < today` で落とす）。あらすじを読む先が無い。
            #
            # **候補側のあらすじは推薦のためだけにある。** 手で足す欄が要るのは題名・団体・
            # 劇場・期間で、そこにあらすじは出てこない。手で足した記録の内容の傾向は
            # 学習側（`--side rated`）が別に取るので、ここで取っても二重になる。
            if c.get("ended"):
                continue
            f = c["fields"] if isinstance(c["fields"], dict) else {}
            rows.append({"id": c["stage_id"], "title": c["title"][:60],
                         "stage_id": c["stage_id"],
                         "url": url_of(f.get("公式／劇場サイト", ""))})
    else:                                   # 学習側 ── 評価済みの作品
        # **公式 URL は (観劇日, メールの件名) で引く。** 日付だけで引くと、
        # 1 日に 2 本観た日（実データにある）で別の作品の URL を掴む。
        #
        # **URL の出どころを official.jsonl から credits.jsonl に変えた。** official.jsonl は
        # 裏方のクレジットを追いに行った 94 件しか持っておらず、突き合わせられたのは 31 件
        # だった。credits.jsonl は CoRich の一覧そのもので、155 行のうち 130 行に
        # 「公式／劇場サイト」が入っている ── **候補側と同じ欄なので、学習側と候補側で
        # 材料の経路が揃う。**
        import measure_nets as M
        import rate_performances as R
        url_by_show: dict[tuple, str] = {}
        sid_by_show: dict[tuple, str] = {}
        for c in (json.loads(l) for l in CREDITS.read_text(encoding="utf-8").split("\n") if l.strip()):
            f = c.get("fields") or {}
            if isinstance(f, str):
                import ast
                f = ast.literal_eval(f)
            u = url_of(f.get("公式／劇場サイト", ""))
            if u:
                url_by_show[(c.get("date"), c.get("mail_title"))] = u
            if c.get("stage_id"):
                sid_by_show[(c.get("date"), c.get("mail_title"))] = str(c["stage_id"])
        con = R.connect()
        state = R.State("theme", con, R.load_purchases())
        by_key = {w["work_key"]: w for w in state.works}
        for r in M.load_rated():
            w = by_key.get(r["key"], {})
            # **記録に結び付けた公演の id を先に使う。** 手で足した記録にはメールが無いので
            # (観劇日, 件名) の経路が使えず、この行が無いとあらすじが 1 件も取れない
            url, sid = "", str(r.get("stage_id") or "")
            for s in w.get("shows", []):
                p = state.by_uid[s["uid"]]
                url = url_by_show.get((p.get("date"), p.get("title")), "") or url
                sid = sid_by_show.get((p.get("date"), p.get("title")), "") or sid
            rows.append({"id": r["key"], "title": r["title"][:60], "url": url,
                         "stage_id": sid, "verdict": r["verdict"]})
        con.close()
    # **本人が貼り直した公演ページを優先する。** 公式サイトの欄が X アカウントや
    # リンク集を指している公演（あらすじが空だったうちの 23%・[検証 048]）は、
    # **正しい URL さえ分かれば機械が取れる。** 探すのは人、辿るのは機械である。
    hand = HT.load()
    for r in rows:
        h = hand.get(str(r.get("stage_id") or "")) or hand.get(str(r.get("id") or ""))
        if h and h.get("url"):
            r["url"] = h["url"]
    for r in rows:
        html = cached(r["url"]) if r["url"] else ""
        if not html and r["url"] and fetch:
            html, _err = get(r["url"])
        # **CoRich のページを先に置く。** その公演のことしか書いていないので確度が高い。
        # 公式サイトは劇団のトップページであることがあり、他公演の話が混ざる。
        parts = []
        cor = corich_text(r.get("stage_id") or "")
        if cor:
            parts.append("[CoRich の公演ページ]\n" + cor)
        if html:
            parts.append("[公式サイト]\n" + prep(html, 3500))
        r["text"] = "\n\n".join(parts)
    return rows


def body_of(batch: list[dict], version: str) -> str:
    """LLM に渡す本体を作る。**c3 以降は題名を渡す**（c2 は id と本文だけだった）。"""
    if version == "c2":
        return "".join(f"### id: {r['id']}\n{r['text']}\n\n" for r in batch)
    return "".join(f"### id: {r['id']}\n題名: {r['title']}\n{r['text']}\n\n" for r in batch)


# **出力の形を Gemini の構造化出力に強制する。** 以前は自由文から `[...]` を
# 正規表現で切り出していた（崩れた出力を当て推量で拾う作りだった）。型を渡す側の
# 責務にすることで、崩れた出力そのものを起こさせない（`llm-api` スキルの守り 3）。
THEME_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "id": {"type": "STRING"},
            "synopsis": {"type": "STRING"},
            "elements": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {"kind": {"type": "STRING"}, "word": {"type": "STRING"}},
                    "required": ["kind", "word"],
                },
            },
        },
        "required": ["id", "synopsis", "elements"],
    },
}


def ask(batch: list[dict], model: str, version: str = PROMPT_VERSION) -> list[dict]:
    body = body_of(batch, version)
    try:
        got, _meta = LLM.ask(PROMPTS[version] + body, schema=THEME_SCHEMA,
                             model=model, timeout=600)
    except LLM.SafetyBlocked as e:
        # **安全フィルタで止まった分は、「取れなかった」に混ぜない。** ここで空を
        # 返す先（`main` の `run`）は「次回の実行で拾う」扱いになるので、実質は
        # 混ざってしまうが、少なくとも理由をログには残す（`llm-api` スキルの守り 4）
        print(f"  {e}（{len(batch)} 件ぶん）", flush=True)
        return []
    except LLM.LLMError as e:
        print(f"  {e}", flush=True)
        return []
    return got if isinstance(got, list) else []


def synopsis_of(stage_id: str, title: str = "") -> str:
    """1 件だけ、あらすじを調べて返す。**「観ればよかった」の登録が使う**入口。

    バッチ処理（`targets`）と違って、公式サイトの URL は解決しない ── 見逃した公演には
    そもそも記録が無いので、本人が貼り直した URL（`hand_themes`）を引く鍵が無い。
    CoRich の公演ページの本文（`corich_text`）だけを材料にする。**抜き出したら、
    渡した本文に実在するかを検査してから返す**（`verbatim`）── ここだけ検査を
    省くと、この 1 件だけモデルの創作を見抜けなくなる。
    """
    text = corich_text(stage_id)
    if not text:
        return ""
    got = ask([{"id": str(stage_id), "title": title, "text": text}], MODEL)
    row = next((g for g in got if str(g.get("id")) == str(stage_id)), None)
    syn = str((row or {}).get("synopsis") or "").strip()
    return syn[:300] if syn and verbatim(syn, text) else ""


def enrich_one(stage_id: str, work_key: str, title: str) -> str:
    """1 件だけ、あらすじと題材を調べて `themes.jsonl` に書く。**押した直後の
    1 件ぶんの材料**（`enrich.stage`）が呼ぶ入口。（起案者の指示・2026-08-26 ──
    「登録した過去公演は…自動でクレジットやあらすじを読み取って日記帳上に表示して
    ほしい」）。

    ## 2 つの側に書く（起案者の指摘・2026-08-26 ──「ハードプロブレムのあらすじが
    取得できてるけど、お気に入りのほうでは取得できていないことになっているのはなぜ？」）

    **`themes.jsonl` は `(side, id)` の 2 本立てである。** 日記帳（観た記録）は
    `side="rated"`／`id=work_key` を読み（`app._synopsis_by_key`）、お気に入りや
    おすすめ（これから観られる公演）は `side="candidate"`／`id=stage_id` を読む
    （`recommend2.py` の `_overlay_themes`）。**別の鍵なので、片方に書いても
    もう片方には出ない。** お気に入り63は日記帳の記録でもありお気に入りの
    候補でもある（結び付けた公演を、たまたま両方が指している）ので、この食い違いが
    見えた。**本文は同じ 1 回の取得・1 回の LLM 呼び出しで足りる** ── 見ているのは
    同じ CoRich の公演ページなので、`rated` 側だけ調べて `candidate` 側は調べない、
    ということはしない。両方の行を書く。

    **バッチ（`main`）が書く形式（`side`/`id`/`title`/`url`/`synopsis`/`elements`/
    `reason`/`model`/`prompt_version`/`at`）とそろえて書く。** 揃えておかないと、
    次にバッチを回したときにこの行を「済み」と認識できず、同じ 1 件に 2 度目の
    LLM 呼び出しが起きる。

    **すでに両方書いてあれば、何もしない。** 結び付け直すたびに呼ばれうるので、
    同じ行が増え続けないようにする（追記のみで、書き換えはしない ── バッチ側の
    「済み」判定と同じ、行の先頭を消さない約束にそろえる）。**片方だけ済んでいる
    ときは、もう片方だけを書く**（LLM は呼び直さない ── `candidate` 側の本文取得
    だけをやり直し、結果は使い回す）。

    **公式サイトの本文までは見に行かない**（`synopsis_of` と同じ簡略化）。
    見に行くのは CoRich の公演ページ本文だけである。
    """
    keys = {"rated": ("rated", str(work_key)), "candidate": ("candidate", str(stage_id))}
    done: dict[str, dict] = {}
    if OUT.exists():
        for l in OUT.read_text(encoding="utf-8").split("\n"):
            if not l.strip():
                continue
            r = json.loads(l)
            for side, key in keys.items():
                if (r.get("side"), r.get("id")) == key:
                    done[side] = r
    missing = [s for s in ("rated", "candidate") if s not in done]
    if not missing:
        both_ok = all(done[s].get("synopsis") for s in ("rated", "candidate"))
        return ("あらすじはすでに両方調べてありました" if both_ok
                else "あらすじは公演ページに見つかりませんでした（調べ済み）")
    # **もう片方の側にすでに調べた結果があれば、それを使い回す。** 同じ公演ページの
    # 本文を指しているので、LLM を呼び直す理由が無い（「見つからなかった」という
    # 結果も、調べ済みの事実として使い回す）
    prior = next((done[s] for s in done), None)
    if prior is not None:
        syn, elements, reason = (prior.get("synopsis") or "", prior.get("elements") or [],
                                 prior.get("reason") or "")
    else:
        text = corich_text(stage_id)
        syn, elements, reason = "", [], "本文なし"
        if text:
            got = ask([{"id": str(stage_id), "title": title, "text": text}], MODEL)
            g = next((x for x in got if str(x.get("id")) == str(stage_id)), None)
            raw_syn = str((g or {}).get("synopsis") or "")[:400]
            vb = verbatim(raw_syn, text) if raw_syn else False
            syn = raw_syn if vb else ""
            elements = ([e for e in ((g or {}).get("elements") or [])
                        if isinstance(e, dict) and e.get("word")]
                       [:MAX_ELEMENTS.get(PROMPT_VERSION, 8)] if vb else [])
            reason = "" if (vb or not raw_syn) else "本文に無い"
    url = f"https://stage.corich.jp/stage/{stage_id}"
    ids = {"rated": str(work_key), "candidate": str(stage_id)}
    lines = []
    for side in missing:
        lines.append(json.dumps({"side": side, "id": ids[side], "title": title[:60],
                                 "url": url, "synopsis": syn, "elements": elements,
                                 "reason": reason, "model": MODEL,
                                 "prompt_version": PROMPT_VERSION,
                                 "at": datetime.date.today().isoformat()},
                                ensure_ascii=False))
    with _lock:
        with OUT.open("a", encoding="utf-8") as fp:
            fp.write("\n".join(lines) + "\n")
    return ("あらすじを取り込みました（日記帳・お気に入り両方）" if syn
            else "あらすじは公演ページに見つかりませんでした")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--side", choices=["candidate", "rated", "both"], default="both")
    ap.add_argument("--batch", type=int, default=6)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="0 なら全件")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--refresh", action="store_true", help="版を上げるとき。全件を引き直す")
    ap.add_argument("--prompt-version", default=PROMPT_VERSION, choices=sorted(PROMPTS),
                    help="測り直しのために古い版を指定する。既定は最新版")
    ap.add_argument("--redo-old-version", action="store_true",
                    help="古い版で取った行だけを引き直す（--refresh と違い、今の版の行は触らない）")
    ap.add_argument("--no-fetch", action="store_true", help="キャッシュにあるページだけ使う")
    ap.add_argument("--recheck", action="store_true",
                    help="LLM を呼ばず、既存の抽出が本文に実在するかだけ検査し直す")
    a = ap.parse_args()

    # **「本文なし」は抽出済みではない。** 取りに行く先を直せば本文が出てくることがある
    # （学習側の URL の出どころを official.jsonl から credits.jsonl に変えたら 31 → 56 件に増えた）。
    # 済みに数えると、直した経路が次の実行で使われない。
    # **版を上げただけで全件を引き直さない。** 直す前は、済みの判定に
    # 「版とモデルが今と同じ行だけ」という条件が付いていたので、**`PROMPT_VERSION` を
    # 上げた次の実行が、黙って 909 件を引き直す**（LLM の呼び出しが 150 回起きる）作りだった。
    # 引き直すかどうかは費用と競合の判断が要るので、**`--refresh` を明示したときだけにする。**
    # 版が上がったあとの新しい行は新しい版で取れるので、直りは新規から入る。
    #
    # **代わりに、混ざった版を数えて表示する。** 版をまたいで取得率を比べるときに、
    # 「どの版で取った行が何件あるか」が分からないと数字の意味が変わる。
    done: set[tuple[str, str]] = set()
    notext: set[tuple[str, str]] = set()
    versions: dict[str, int] = {}
    if OUT.exists() and not a.refresh:
        for l in OUT.read_text(encoding="utf-8").split("\n"):
            if l.strip():
                r = json.loads(l)
                # **落とした行は済みにしない。** 「本文なし」は取りに行く先を直せば本文が
                # 出てくることがあり、**「本文に無い」（モデルが本文に無いことを書いた）は
                # 取り直せば本文どおりの答えが出ることがある。** どちらも次の実行で挑ませる
                # ── 取り直しても駄目なら、実在検査が同じ判定でまた落とすだけである。
                # **`--recheck` の事故で落ちた行を取り戻す道も、ここになる。**
                if r.get("reason") in ("本文なし", "本文に無い"):
                    notext.add((r["side"], r["id"]))
                elif a.redo_old_version and r.get("prompt_version") != a.prompt_version:
                    # **古い版の行だけを挑ませる。** 版が混ざったまま残ると、版で絞って
                    # 読む側（`net_c_axes.py`）が古い抽出を標本にしてしまう。
                    # **`--refresh` は全件を捨てるので、混ざりを直すには強すぎる。**
                    pass
                else:
                    done.add((r["side"], r["id"]))
                    v = f"{r.get('prompt_version')}/{r.get('model')}"
                    versions[v] = versions.get(v, 0) + 1
    if versions:
        mix = "／".join(f"{v} {n} 件" for v, n in sorted(versions.items()))
        print(f"抽出済みの版: {mix}（いまの版は {a.prompt_version}/{a.model}）")
        if any(not v.startswith(f"{a.prompt_version}/") for v in versions):
            print("    **古い版の行は済みとして扱う。引き直すなら --refresh を付ける。**")
    if a.refresh and OUT.exists():
        OUT.unlink()

    if a.recheck:
        # **照合する本文が無いことを「本文に無い」と数えてはいけない。**
        # 直す前は (1) `--side rated` でも themes.jsonl の全行を検査し、(2) 照合先が
        # 引けなかった行を落としていたので、**候補側 522 件のあらすじと要素が
        # 「本文に無い」として一度に消えた。** 検査は「渡した本文に実在するか」を測るもので、
        # **本文を引けなかったことは、その判定の材料が無いという意味である。**
        # そこで (1) 検査するのは --side で指定した側だけにし、
        # (2) 照合先が無い行は**触らずに数える**（落とすのは、本文があって一致しないときだけ）。
        rows = [json.loads(l) for l in OUT.read_text(encoding="utf-8").split("\n") if l.strip()]
        sides = ["rated", "candidate"] if a.side == "both" else [a.side]
        src = {}
        for side in sides:
            for t in targets(side, fetch=False):
                src[(side, t["id"])] = t["text"]
        kept = dropped = nosrc = 0
        for r in rows:
            if r["side"] not in sides or not r["synopsis"]:
                continue
            text = src.get((r["side"], r["id"]), "")
            if not text:                        # 照合先が引けない ── **判定しない**
                nosrc += 1
            elif verbatim(r["synopsis"], text):
                kept += 1
            else:
                r["synopsis"], r["elements"], r["reason"] = "", [], "本文に無い"
                dropped += 1
        OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                       encoding="utf-8")
        print(f"検査（{'・'.join(sides)}）── 本文に実在 {kept} 件／"
              f"本文に無いので落とした {dropped} 件／照合先が引けず判定しなかった {nosrc} 件")
        return 0

    sides = ["rated", "candidate"] if a.side == "both" else [a.side]
    todo: list[dict] = []
    for side in sides:
        rows = targets(side, fetch=not a.no_fetch)
        n_url = sum(1 for r in rows if r["url"])
        n_text = sum(1 for r in rows if r["text"])
        print(f"{side}: {len(rows)} 件／URL あり {n_url}／本文が取れた {n_text}", flush=True)
        for r in rows:
            r["side"] = side
            if (side, r["id"]) in done:
                continue
            if not r["text"]:                       # 本文が無いことも記録する
                if (side, r["id"]) in notext:       # 同じ行を積み上げない
                    continue
                with _lock:
                    with OUT.open("a", encoding="utf-8") as fp:
                        fp.write(json.dumps({"side": side, "id": r["id"], "title": r["title"],
                                             "url": r["url"], "synopsis": "", "elements": [],
                                             "reason": "本文なし", "model": a.model,
                                             "prompt_version": a.prompt_version,
                                             "at": datetime.date.today().isoformat()},
                                            ensure_ascii=False) + "\n")
                continue
            todo.append(r)
    if a.limit:
        todo = todo[:a.limit]
    batches = [todo[i:i + a.batch] for i in range(0, len(todo), a.batch)]
    print(f"LLM に渡すのは {len(todo)} 件（{len(batches)} 回・{a.jobs} 並列・model={a.model}）",
          flush=True)

    counter = [0]

    def run(batch: list[dict]) -> None:
        got = {str(g.get("id")): g for g in ask(batch, a.model, a.prompt_version)
               if isinstance(g, dict)}
        lines = []
        for r in batch:
            g = got.get(str(r["id"]))
            if g is None:
                continue                            # 取れなかった分は次回の実行で拾う
            els = [e for e in (g.get("elements") or [])
                   if isinstance(e, dict) and e.get("word")][:MAX_ELEMENTS.get(a.prompt_version, 5)]
            syn = (g.get("synopsis") or "")[:400]
            vb = verbatim(syn, r["text"]) if syn else False
            if syn and not vb:                  # **本文に無いものは落とす**（出典が付けられない）
                syn, els = "", []
            lines.append(json.dumps({"side": r["side"], "id": r["id"], "title": r["title"],
                                     "url": r["url"], "synopsis": syn,
                                     "elements": els,
                                     "reason": "" if (vb or not g.get("synopsis")) else "本文に無い",
                                     "model": a.model, "prompt_version": a.prompt_version,
                                     "at": datetime.date.today().isoformat()},
                                    ensure_ascii=False))
        with _lock:
            with OUT.open("a", encoding="utf-8") as fp:
                fp.write("\n".join(lines) + ("\n" if lines else ""))
            counter[0] += 1
            print(f"  {counter[0]}/{len(batches)} 回目 ── {len(lines)} 件書き出し", flush=True)

    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        list(ex.map(run, batches))

    rows = [json.loads(l) for l in OUT.read_text(encoding="utf-8").split("\n") if l.strip()]
    syn = [r for r in rows if r["synopsis"]]
    print(f"\n■ 抽出の結果 ── {len(rows)} 件中、あらすじが取れたのは {len(syn)} 件"
          f"（{len(syn)/max(len(rows),1)*100:.0f}%）")
    for side in sides:
        s = [r for r in rows if r["side"] == side]
        ok = [r for r in s if r["synopsis"]]
        print(f"   {side}: {len(ok)}/{len(s)} 件（{len(ok)/max(len(s),1)*100:.0f}%）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
