#!/usr/bin/env python3
"""付けた評価を使って、網 B（作り手の名簿）が働くかを測る。

#000006 の検証項目のうち、評価が付いてから初めて測れるものを扱う。

  V26  評価の偏り ── △ または × が 2 割以上あるか
       （網 B・C は「全体との差」で寄与を出すので、◎○ に偏ると寄与が恒等的に 0 になる）
  V13  網 B の一致密度 ── 名簿に 1 人でも一致する公演が候補の 1 割を超えるか
  V21b 縮約の引き寄せ先 ── 人物単独／役職ごと／公演団体のどれで当たり率が立つか
  判別力 ── 名簿から出した強さが、実際の評価の順位を当てられるか（leave-one-out の AUC）

    python3 tools/review/measure_nets.py

評価は data/review/ratings.db、クレジットは data/credits/credits.jsonl から読む。
どちらも端末内のファイルで、外へは何も出さない。
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import rate_performances as R  # noqa: E402

CREDITS = ROOT / "data" / "credits" / "credits.jsonl"

GRADES = ["◎", "○", "△", "×"]
# 企画書 4 章の重み。ここでは正例／負例の切り方を 2 通り比べるためにも使う。
WEIGHT = {"◎": 1.0, "○": 0.7, "△": 0.3, "×": 0.0}

# 役職の重み（企画書 4 章「演出・脚本を大きく、出演者を中、制作を小さく」）
ROLE_WEIGHT = {"演出": 1.0, "脚本": 1.0, "出演": 0.6}
# 同じ役職の別名。**役職ごとに割る設計なので、揺れると同じ人が別の役職に分かれる** ──
# 実データで作り手30が「作」「脚本」「演出」の 3 つに分かれていた（V43）。
ROLE_ALIAS = {"作": "脚本", "訳": "翻訳", "舞台美術": "美術", "衣装": "衣裳",
              "照明デザイン": "照明", "音響効果": "音響", "美術デザイン": "美術"}
DEFAULT_ROLE_WEIGHT = 0.4

SMOOTH_A, SMOOTH_B = 1, 2      # 当たり率 (o+1)/(n+2)
CONF_K = 3                     # 信頼度 n/(n+3)
TOP_N = 3                      # 寄与が正の上位 3 名の和


def norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").strip()


# ---------------------------------------------------------------- クレジットを読む

_PAREN = re.compile(r"[（(][^）)]*[）)]")
# **人名を「・」で無条件に割ってはいけない。**「ボブ・ウォルトン」は 1 人である。
# ただし「作り手26・作り手18」のように**両側に漢字がある**場合は 2 人なので割る。
_SPLIT = re.compile(r"[、,，／/\n]")
_MIDDOT_KANJI = re.compile(r"(?<=[一-龥])・(?=[一-龥])")
# 「役職：名前」が 1 行に複数並ぶことがある（「美術:石原敬　音響:早川毅」）
_PAIRS = re.compile(r"([^\s　：:]{1,12})[：:][\s　]*([^：:]{2,40}?)(?=(?:[^\s　：:]{1,12}[：:])|$)")
# **【役職】名前 の記法。** 劇場3などが使う。これを扱わないと
# 「【衣裳】前田文子」がまるごと役職名として名簿に入る（実際に n=7 で上位に出た）。
_BRACKET = re.compile(r"[【［《]\s*([^】］》]{1,12})\s*[】］》]\s*([^【［《\n]{2,60})")
_ROLE_LINE = re.compile(r"^([^\s　]{1,14})[\s　]+(.+)$")
# スタッフ欄には日付・会場・見出しが混ざる。人名の欄ではないので落とす。
_NOT_NAME = re.compile(r"(\d{4}年|\d+月|\d+日|[都道府県]\s|劇場|ホール|シアター|"
                       r"^[▶●○・\-—=]|^[A-Z ]{3,}$|上演|公演$|チケット|料金)")
_ROLE_PREFIX = re.compile(r"^(脚色|翻訳|上演台本|原案|原作|作|演出|振付|訳)[\s　]*")
# 「※Wキャスト」「（Wキャスト）」のような注記は名前ではない
_NOTE = re.compile(r"[※*＊].*$")
# **行頭の【役職】タグ。** `_BRACKET` はスタッフ欄で「1 行に【役職】名前」が複数並ぶ書式
# を扱うためのものだが、**出演・脚本・演出の 3 欄は `_names()` を直接呼ぶので通らない。**
# 「【演出】 笹部博司」のように書くと、`_ROLE_PREFIX` は括弧の付かない役職しか剥がせず、
# 残った角括弧が下の安全策（`"[【】［］《》]"` を含む語を捨てる）に当たって**名前ごと
# 消えていた**（起案者の指摘・2026-08-26 ──「名簿に 4 人書いているのに 3 人しか
# 反映されていない」）。役職の中身は問わず、行頭の括弧タグだけを剥がす。
_LEAD_TAG = re.compile(r"^[【［《][^】］》]{1,20}[】］》][\s　]*")

# **役職は語彙で縛る。** 縛らないと登場人物名（「ティガー」）や
# 見出し（「CAST-Team」）が役職として名簿に入る。
ROLE_VOCAB = {
    "出演", "脚本", "作", "演出", "翻訳", "原作", "原案", "脚色", "上演台本", "訳",
    "音楽", "作曲", "編曲", "音楽監督", "振付", "美術", "舞台美術", "照明", "音響",
    "衣裳", "衣装", "ヘアメイク", "メイク", "舞台監督", "演出助手", "舞台監督助手",
    "宣伝美術", "宣伝写真", "写真", "映像", "制作", "プロデューサー", "企画", "主催",
    "技術監督", "小道具", "大道具", "殺陣", "方言指導", "歌唱指導", "演奏", "指揮",
    # V44 で実データから足したもの。**閉じた語彙のままだと本物の役職が
    # 「スタッフ」に丸められる** ── 「劇中映像」「票券」「宣伝プロデューサー」は役職である。
    "宣伝", "票券", "協力", "製作", "指導", "振付", "コーディネーター", "オーケストラ",
    "アクション", "マジック", "マニピュレーター", "ピアノ", "台本", "作詞", "潤色",
    "オペレーション", "デスク", "プロダクション", "コンダクター", "コーディネート",
}


def _clean_role(role: str) -> str:
    """役職を正規化し、語彙に無ければ「スタッフ」に丸める。

    **語彙は閉じているが、含んでいれば拾う。** 複合の役職（「脚本・演出」「企画・製作」
    「パルクール演出」）や記号つき（「■作・演出」）が実データに多く、
    完全一致だけだと**本物の役職が半分以上「スタッフ」に落ちていた**（V44 で実測 54%）。
    含まれない語は「スタッフ」に落とす ── 役名（「プー」「クリストファー・ロビン」）や
    人名の姓（「岸」「中井」）を役職として拾わないための守りである。
    """
    r = norm(role).strip("　 :：・")
    r = re.sub(r"^[■□●◆○◇\-—─・\*]+", "", r).strip()
    r = re.sub(r"(デザイン|プラン|ﾃﾞｻﾞｲﾝ)$", "", r).strip()
    if r in ROLE_VOCAB:
        return r
    # 含んでいれば拾う。**語頭を優先する** ── 役職名は分野が先に来るので、
    # 「制作デスク」は「制作」、「映像オペレーション」は「映像」が正しい。
    # 語頭に無ければ、含まれる中で最も長いものを採る（「パルクール演出」→「演出」）。
    head = [v for v in ROLE_VOCAB if r.startswith(v)]
    if head:
        return max(head, key=len)
    hit = [v for v in ROLE_VOCAB if v in r]
    if hit:
        return max(hit, key=len)
    return "スタッフ"


def _names(text: str) -> list[str]:
    out = []
    text = _NOTE.sub("", text or "")
    # **括弧は分割より先に外す。** 後にすると、括弧の中の所属が区切り記号で割れる ──
    # 「鎌塚慎平(劇団・木製ボイジャー14号)」が「鎌塚慎平(劇団」と「木製ボイジャー14号)」に、
    # 「正門良規(Aぇ!group、関西ジャニーズJr.)」が 2 つに割れていた（V43）。
    text = _PAREN.sub("", text)
    for part in _MIDDOT_KANJI.sub("\n", _SPLIT.sub("\n", text)).split("\n"):
        n = norm(part)
        n = _LEAD_TAG.sub("", n)
        n = _ROLE_PREFIX.sub("", n).strip("　 :：・")
        # **姓名のあいだの空白を落とす。** 実データで「加藤 温」（8 本）と「加藤温」（2 本）が
        # 別人として数えられ、信頼度が 0.73 と 0.40 に割れていた（V15）。
        n = re.sub(r"[\s　]", "", n)
        # 括弧記法の残骸や役職語そのものは人名ではない
        if not n or re.search(r"[【】［］《》]", n) or n in ROLE_VOCAB:
            continue
        if 2 <= len(n) <= 20 and not _NOT_NAME.search(n):
            out.append(n)
    return out


def canon_role(role: str) -> str:
    r = norm(role)
    return ROLE_ALIAS.get(r, r)


def parse_credits(fields: dict) -> list[tuple[str, str]]:
    """(役職, 人物名) の並びを返す。

    スタッフ欄の書式は 3 通りある ── 行頭に役職を置いて空白で名前を続けるもの、
    「役職：名前」を 1 行に複数並べるもの、前の行の役職が続くもの。
    """
    out: list[tuple[str, str]] = []
    for role in ("出演", "脚本", "演出"):
        for n in _names(fields.get(role, "")):
            out.append((canon_role(role), n))
    last = ""
    for raw in (fields.get("スタッフ") or "").splitlines():
        line = raw.rstrip()
        if not line.strip() or _NOT_NAME.search(norm(line)):
            continue
        brackets = _BRACKET.findall(norm(line))
        if brackets:
            for role, body in brackets:
                last = _clean_role(role)
                for n in _names(body):
                    out.append((canon_role(last), n))
            continue
        # 「ディレクター：」のように役職だけの行は、次の行以降の見出しになる。
        # **これを拾わないと、続く人名がすべて役職不明に落ちる**（V43 で実測 24%）。
        head = re.match(r"^[\s　]*([^\s　：:]{2,14})[：:][\s　]*$", norm(line))
        if head:
            last = _clean_role(head.group(1))
            continue
        pairs = _PAIRS.findall(norm(line))
        if pairs:
            for role, body in pairs:
                last = _clean_role(role)
                for n in _names(body):
                    out.append((canon_role(last), n))
            continue
        m = _ROLE_LINE.match(line)
        if m and not line.startswith(("　", " ")):
            last, body = _clean_role(m.group(1)), m.group(2)
        else:
            body = line
        for n in _names(body):
            out.append((canon_role(last) or "スタッフ", n))
    # 同じ人物が同じ役職で重複しても 1 回だけ数える
    return sorted(set(out))


def _fields_by_stage() -> dict[str, dict]:
    """公演の id → クレジットの表。**手で足した記録の材料はここから引く。**

    購入確認メールから導ける作品は (観劇日, メールの件名) でクレジットに結び付くが、
    **手で足した記録にはメールが無い**ので、その経路が使えない。代わりに、登録のときに
    本人が候補から選んだ公演の id を使う（`works.stage_id`）。

    **3 つの控えを重ねる。** `linked.jsonl` は題名から探し直して結び付けた公演、
    `credits.jsonl` は過去に観た公演、`candidates.jsonl` はこれから／最近の公演である。
    **結び付けた分を先に置く** ── 探し直したものは日付と題名の両方で当てているので、
    他の控えより確かである。
    """
    out: dict[str, dict] = {}
    for path in (ROOT / "data" / "credits" / "linked.jsonl", CREDITS,
                 ROOT / "data" / "review" / "candidates.jsonl"):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            c = json.loads(line)
            sid = str(c.get("stage_id") or "")
            f = c.get("fields") or {}
            if isinstance(f, str):
                import ast
                f = ast.literal_eval(f)
            if sid and isinstance(f, dict) and f:
                out.setdefault(sid, f)
    return out


def load_rated(*, include_unrated: bool = False) -> list[dict]:
    """評価が付いた作品を、クレジットと突き合わせて返す。

    ## `include_unrated` ── 評価が付いていない記録も返す（2026-08-24）

    **学習は ◎ だけを正例に使うので、既定は評価が付いたものだけである**（検証で決めた
    ことなので変えない）。**探す画面だけが評価の有無を問わない** ── 起案者の指示で
    「探した結果からその場で評価できるように」した以上、**評価が無い記録が出てこないと、
    そこから評価する道が閉じる。** そこで呼ぶ側が明示したときだけ、評価の無い記録を
    `verdict` を空にして混ぜる。**学習側の呼び出しは既定のままなので、正例の定義は動かない。**

    ## 手で足した記録も入れる（2026-08-24・起案者の指示）

    **「手で足した公演も推薦の情報に入るようにして」。** それまでは購入確認メールから
    導ける作品だけを見ており、**招待・当日窓口・人に取ってもらった分は、評価を付けても
    名簿にも内容の傾向にも 1 件も効かなかった。**

    **記録に残らない経路ほど、思い入れのある観劇が通る**（`app.add_work` の注記）。
    その分が学習から丸ごと落ちていたのは、企画の前提と反対である。

    **クレジットは公演の id で引く。** メールが無いので (観劇日, 件名) の経路は使えない。
    id が無い記録（手で打った分）は**人物も会場も空のまま入れる** ── 評価が付いている
    以上、全体の ◎ 率（基準線）の分母には数える。**メールから導ける作品でも、
    クレジットが引けないものは同じ扱いで入っている**ので、揃えた形である。
    """
    purchases = R.load_purchases()
    con = R.connect()
    state = R.State("measure", con, purchases)
    saved = R.read_works(con)

    # **まだ 1 度も取り寄せていない状態を、失敗として扱わない。** 初めて使う人の端末には
    # このファイルが無い（2026-08-24 の実測でここで止まった）。無いときはクレジットが
    # 空なだけで、評価済みの作品を数えること自体はできる
    credits = [json.loads(l) for l in
               (CREDITS.read_text(encoding="utf-8").split("\n") if CREDITS.exists() else [])
               if l.strip()]
    by_key = {(c.get("date"), c.get("mail_title")): c for c in credits}
    fields = _fields_by_stage()          # **1 度だけ読む**（作品ごとに読み直さない）
    hand = R.read_hand(con)              # 人が手で入れた出演者（公演ページが無い公演）

    rated = []
    for w in state.works:
        row = saved.get(w["work_key"]) or {}
        if row.get("verdict") not in GRADES and not include_unrated:
            continue
        people: list[tuple[str, str]] = []
        troupes: set[str] = set()
        sid = ""
        for s in w["shows"]:
            p = state.by_uid[s["uid"]]
            c = by_key.get((p.get("date"), p.get("title")))
            if not c:
                continue
            sid = sid or str(c.get("stage_id") or "")
            people += parse_credits(c.get("fields") or {})
            venue = norm((c.get("fields") or {}).get("劇場", ""))
            if venue:
                troupes.add(venue)
        # **メールから引けなかったら、記録に結び付けた公演で引き直す。**
        # 評価済み 91 作品のうちクレジットが引けたのは 54 件で、**残り 37 件は
        # 評価が付いているのに名簿へ 1 人も出していない。** 結び付ける口を画面に作った
        # 以上、結び付けたものはここで効かなければ意味が無い
        link = str((row.get("stage_id") or ""))
        if not people and link:
            f = fields.get(link) or {}
            if f:
                people = parse_credits(f)
                venue = norm(f.get("劇場", ""))
                if venue:
                    troupes.add(venue)
                sid = sid or link
        # **手で入れた分は、足す。**（起案者の報告 2026-08-24 ──「どれだけ試しても
        # ポスターが違ったり、出演者が取得できなかったりした」）**公演ページが存在しない
        # 公演では、本人が打つ以外に名簿へ入る道が無い。** 置き換えではなく足すのは、
        # ページから取れている分を消す理由が無いからである（消したいときは結び付けを外す）。
        # **読み取りは公演ページと同じ `parse_credits` を通す** ── 手で入れた分にだけ
        # 別の規則を作ると、役職の丸め方が 2 通りになる。
        hf = (hand.get(w["work_key"]) or {}).get("fields") or {}
        if hf:
            people += parse_credits(hf)
        rated.append({
            "key": w["work_key"], "title": w["title_display"],
            "date": w["first_date"], "verdict": row.get("verdict") or "",
            "stage_id": sid or link,
            "times": w["times"], "people": sorted(set(people)), "venues": sorted(troupes),
            "manual": False,
        })
    rated += _manual_rated(con, state, saved, fields, hand,
                           include_unrated=include_unrated)
    con.close()
    return rated


def _manual_rated(con, state, saved: dict, fields: dict, hand: dict | None = None,
                  *, include_unrated: bool = False) -> list[dict]:
    """手で足した記録のうち、評価が付いているもの。

    **取り消した分と、同じ公演としてまとめた分は入れない。** 画面の一覧から外したものが
    学習にだけ残ると、**外した理由（まちがって拾われた）が推薦に効き続ける。**
    """
    hand = hand or {}
    merges = R.read_merges(con)
    dropped = {u[5:] for u, _p in R.read_excluded(con) if u.startswith("work:")}
    # **同じ公演を 2 度数えない。** `work_key` は「題名の鍵＋初日」なので、束ね方が変わって
    # 鍵が変わると、**古い鍵の行が `works` に取り残される** ── 実データで「受取人不明」が
    # 同じ日付で 2 行あり、どちらにも ◎ が付いていた。取り残された行をそのまま学習に
    # 入れると、**1 本の観劇が 2 本として基準線に効く。**
    #
    # **判定は `load_works` の束ね方に合わせる**（題名の鍵が同じで、初日が
    # `RUN_GAP_DAYS` 以内）。人が「同じ公演だ」と答えた分は merges で先に外れている。
    derived = {}
    for w in state.works:
        derived.setdefault(w["work_key"].rsplit("#", 1)[0], []).append(w["first_date"] or "")

    def already(key: str) -> bool:
        base, _, day = key.rpartition("#")
        for other in derived.get(base, []):
            if not day or not other or day == other:
                return True
            try:
                if abs((date.fromisoformat(day) - date.fromisoformat(other)).days) \
                        <= R.RUN_GAP_DAYS:
                    return True
            except ValueError:
                return True
        return False

    out = []
    for key, row in saved.items():
        if key in state.by_key or key in merges or key in dropped:
            continue
        if row.get("verdict") not in GRADES and not include_unrated:
            continue
        if already(key):
            continue
        f = fields.get(str(row.get("stage_id") or "")) or {}
        venue = norm(f.get("劇場", ""))
        # **手で足した記録こそ、手で入れた出演者が要る。** 招待・当日窓口で観た公演は
        # 購入確認メールに残らないうえ、公演ページも無いことが多い
        hf = (hand.get(key) or {}).get("fields") or {}
        people = parse_credits(f) if f else []
        if hf:
            people += parse_credits(hf)
        out.append({
            "key": key, "title": R.norm(row.get("title") or ""),
            "date": row.get("first_date") or "", "verdict": row.get("verdict") or "",
            "stage_id": str(row.get("stage_id") or ""),
            "times": row.get("times") or 1,
            "people": sorted(set(people)),
            "venues": [venue] if venue else [], "manual": True,
        })
    return out


# ---------------------------------------------------------------- 網 B

def build_roster(rows: list[dict], positive) -> dict[tuple[str, str], tuple[int, float]]:
    """(役職, 人物) → (観た本数 n, 正例ぶん o)。

    `positive` は真偽を返してもよく、0〜1 の重みを返してもよい。重みを使うと
    ◎ と ○ の差を捨てずに数えられる（企画書 4 章の 1.0/0.7/0.3/0）。
    """
    tally: dict[tuple[str, str], list[float]] = collections.defaultdict(lambda: [0, 0.0])
    for r in rows:
        pos = float(positive(r["verdict"]))
        for key in r["people"]:
            tally[key][0] += 1
            tally[key][1] += pos
    return {k: (int(v[0]), v[1]) for k, v in tally.items()}


def interest_credits(react: dict, missed: list[dict]) -> list[tuple[str, str]]:
    """興味あり・観ればよかったから来た (役職, 人物) の並び（起案者の指示・2026-08-26 ──
    「『観ればよかった』で挙がった人名は『興味あり』のボタンを押した扱いと同じにして、
    推薦に反映させて」）。

    **「興味あり」自体は、これまで名簿（roster）に一切効いていなかった。** 押した反応
    （`reaction.interest`）は束の振り分け（追いかけている一覧に入れる）にしか使っておらず、
    人物の当たり率は ◎ を付けた記録（`load_rated`）だけから作っていた。**その橋がここである。**

    **観ればよかったも同じ扱いにする。** 見逃して悔しいと自分で登録した公演は、
    「興味あり」と同じ「もっと知りたい」の意思表示なので、区別しない。

    候補の公演ページの材料（`_fields_by_stage`）が無い stage_id（提示が古く控えに
    残っていない等）は静かに飛ばす ── 反応そのものは残っているので、材料が揃えば
    次の実行から効く。
    """
    fields_by_stage = _fields_by_stage()
    out: list[tuple[str, str]] = []
    for sid, r in react.items():
        if r.get("interest") == 1:
            f = fields_by_stage.get(str(sid))
            if f:
                out.extend(parse_credits(f))
    for f in missed:
        out.extend(parse_credits(f))
    return out


def add_interest_roster(roster: dict[tuple[str, str], tuple[int, float]],
                         credits_list: list[tuple[str, str]], weight: float
                         ) -> dict[tuple[str, str], tuple[int, float]]:
    """興味あり・観ればよかったの信号を、◎ より弱い正例として名簿に重ねる。

    **◎ の基準（`base`）は動かさない。** 呼ぶ側は `base` を「評価が付いた記録」だけから
    計算したあとにこれを呼ぶこと。**興味ありには対になる負例が無い**（「興味なし」を
    押した公演の作り手を負例として数えはしない ── 見送った理由は人ではなく作品や
    内容にあることが多いため）。**一方的な正の信号を `base` の計算に混ぜると、
    当たり率が実態より高く出て、◎ の重みが相対的に薄まる**（実測: いまの反応 41 件を
    そのまま `rated` に混ぜると、基準は 0.38 → 0.57 に跳ね上がる）。

    **重みは ◎ より弱くする。** 見たい・見逃したと思っただけで、実際に観て評価した
    わけではないため、`n`（本数）は 1 件として数えるが `o`（当たりぶん）には
    `weight`（< 1.0）しか足さない。**この重みは AUC で測っていない**（◎/○/△/× の
    1.0/0.7/0.3/0 や役職の重みのように検証済みの値ではない、新しい信号である）ので、
    実際の当たり方を見ながら調整が要る前提で低めの値から始める。
    """
    out = {k: list(v) for k, v in roster.items()}
    for key in credits_list:
        cur = out.setdefault(key, [0, 0.0])
        cur[0] += 1
        cur[1] += weight
    return {k: (int(v[0]), v[1]) for k, v in out.items()}


def score(row: dict, roster: dict, base: float, *, by_role: bool = True) -> float:
    """企画書 4 章の式。寄与が正の上位 TOP_N 名の和。"""
    parts = []
    for role, person in row["people"]:
        key = (role, person) if by_role else ("*", person)
        n, o = roster.get(key, (0, 0))
        if n == 0:
            continue
        rate = (o + SMOOTH_A) / (n + SMOOTH_B)
        conf = n / (n + CONF_K)
        w = ROLE_WEIGHT.get(role, DEFAULT_ROLE_WEIGHT) if by_role else 1.0
        c = (rate - base) * conf * w
        if c > 0:
            parts.append(c)
    return sum(sorted(parts, reverse=True)[:TOP_N])


def merge_roles(roster: dict) -> dict:
    """役職を無視して人物だけで数え直す（縮約の引き寄せ先の比較用）。"""
    out: dict[tuple[str, str], list[float]] = collections.defaultdict(lambda: [0, 0.0])
    for (_, person), (n, o) in roster.items():
        out[("*", person)][0] += n
        out[("*", person)][1] += o
    return {k: tuple(v) for k, v in out.items()}


def auc(pairs: list[tuple[float, bool]]) -> float | None:
    """順位の当たり具合。0.5 ででたらめ、1.0 で完全。"""
    pos = [s for s, y in pairs if y]
    neg = [s for s, y in pairs if not y]
    if not pos or not neg:
        return None
    win = sum((a > b) + 0.5 * (a == b) for a in pos for b in neg)
    return win / (len(pos) * len(neg))


def leave_one_out(rows: list[dict], positive, *, by_role: bool,
                  target=None) -> tuple[float | None, list]:
    """1 件を伏せて、残りから作った名簿でその 1 件を評価する。

    `positive` は名簿を作るときの数え方、`target` は当てたい相手。
    分けておかないと、数え方を変えたときに当てる相手も動いて比べられない。
    """
    target = target or (lambda v: bool(positive(v)))
    out = []
    for i, r in enumerate(rows):
        rest = rows[:i] + rows[i + 1:]
        roster = build_roster(rest, positive)
        if not by_role:
            roster = merge_roles(roster)
        base = sum(float(positive(x["verdict"])) for x in rest) / len(rest)
        out.append((score(r, roster, base, by_role=by_role), target(r["verdict"])))
    return auc(out), out


# ---------------------------------------------------------------- 報告

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()

    rows = load_rated()
    c = collections.Counter(r["verdict"] for r in rows)
    total = sum(c.values())
    if total < 30:
        print(f"段階つきの評価が {total} 件しかない。30 件を下限としているので、"
              "先に評価を増やすこと。")
        return 1
    with_credits = [r for r in rows if r["people"]]

    print(f"段階つき作品 {total} 件 / クレジットが取れた作品 {len(with_credits)} 件"
          f"（{len(with_credits) / total * 100:.0f}%）")
    print(f"人物（役職つき）延べ {sum(len(r['people']) for r in with_credits)} 件")

    print("\n■ V26 評価の偏り ── △ または × が 2 割以上あるか")
    for g in GRADES:
        print(f"    {g}  {c[g]:>3} 件  {c[g] / total * 100:>4.0f}%  {'█' * round(c[g] / total * 60)}")
    low = c["△"] + c["×"]
    print(f"    △・× 合わせて {low} 件 = {low / total * 100:.0f}%"
          f"  → 閾値 20% に対して**{'成立' if low / total >= 0.2 else '不成立'}**")
    print(f"    ○ 以上を正例とすると、全体の正率（基準線）は {(c['◎'] + c['○']) / total * 100:.0f}%")
    print(f"    ◎ だけを正例とすると、全体の正率（基準線）は {c['◎'] / total * 100:.0f}%")

    print("\n■ V13 網 B の一致密度 ── 名簿に 1 人でも一致する公演の割合")
    for label, by_role in (("役職つきで数える", True), ("人物だけで数える", False)):
        hit = n_match = 0
        for i, r in enumerate(with_credits):
            rest = with_credits[:i] + with_credits[i + 1:]
            roster = build_roster(rest, lambda v: v == "◎")
            if not by_role:
                roster = merge_roles(roster)
            keys = [(role, p) if by_role else ("*", p) for role, p in r["people"]]
            m = sum(1 for k in keys if roster.get(k, (0, 0))[0] > 0)
            hit += m > 0
            n_match += m
        print(f"    {label}: 一致あり {hit}/{len(with_credits)} 件"
              f"（{hit / len(with_credits) * 100:.0f}%）、1 公演あたり平均 "
              f"{n_match / len(with_credits):.1f} 人が一致")
    print("    → 一致は稀ではない。**二値では絞り込みにならない**というスコア化の前提は正しい")

    print("\n■ 判別力 ── 名簿の強さが評価の順位を当てられるか（leave-one-out の AUC）")
    print("    AUC 0.5 ででたらめ。正例の切り方と、縮約の引き寄せ先を並べて比べる。")
    rowsc = with_credits
    # 名簿を作るときの数え方は 3 通り。当てる相手（正例）は ◎ に固定して比べる。
    ways = (("○ 以上を 1 と数える", lambda v: v in ("◎", "○")),
            ("◎ だけを 1 と数える", lambda v: v == "◎"),
            ("重みで数える（◎1.0 ○0.7 △0.3 ×0）", lambda v: WEIGHT[v]))
    for build_label, build_pos in ways:
        for role_label, by_role in (("役職ごと", True), ("人物だけ", False)):
            a, _ = leave_one_out(rowsc, build_pos, by_role=by_role,
                                 target=lambda v: v == "◎")
            print(f"    {build_label:<28} × {role_label:<8} AUC = "
                  + ("測れない" if a is None else f"{a:.3f}"))
    print("    ※ 当てる相手は「◎ かどうか」に固定してある（○ 以上は 87% なので当てても意味が薄い）")

    print("\n■ V21b 名簿がどれだけ立ち上がっているか")
    roster = build_roster(with_credits, lambda v: v == "◎")
    n_hist = collections.Counter(n for n, _ in roster.values())
    tot = sum(n_hist.values())
    print(f"    役職つきの人物 {tot} 人")
    for k in sorted(n_hist)[:6]:
        print(f"      n = {k}: {n_hist[k]:>4} 人（{n_hist[k] / tot * 100:.0f}%）"
              f"  信頼度 {k / (k + CONF_K):.2f}")
    ge3 = sum(v for k, v in n_hist.items() if k >= 3)
    print(f"    n ≥ 3 の人物 {ge3} 人  → 企画書は「数十人ほしい」としている")
    merged = merge_roles(roster)
    m_hist = collections.Counter(n for n, _ in merged.values())
    m_ge3 = sum(v for k, v in m_hist.items() if k >= 3)
    print(f"    役職を畳んで人物だけにすると {sum(m_hist.values())} 人、n ≥ 3 は {m_ge3} 人")

    print("\n■ 当たり率が高く、観た本数も多い人物（上位 20）")
    base = sum(1 for r in with_credits if r["verdict"] == "◎") / len(with_credits)
    rank = []
    for (role, person), (n, o) in roster.items():
        if n < 2:
            continue
        rate = (o + SMOOTH_A) / (n + SMOOTH_B)
        rank.append(((rate - base) * (n / (n + CONF_K)), n, o, role, person))
    for c0, n, o, role, person in sorted(rank, reverse=True)[:20]:
        print(f"    寄与 {c0:+.3f}  観 {n:>2} 本中 ◎ {o:>2}  {role:<8} {person}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
