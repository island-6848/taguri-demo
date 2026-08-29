#!/usr/bin/env python3
"""推薦の出力と、それに対する反応を残す。

## なぜ要るのか

**出した一覧を残していなかった。** `data/review/recommend2.json` は毎回上書きされるので、
再実行すると前の順位が消える（実際に [検証 021](../../docs/verification/021-first-user-reaction.md)
の初回の順位は上書きで失われ、検証記録の文章からしか復元できなかった）。

**出力側の指標は、その週に何をどの順でどの理由で出したかが残っていないと後から計算できない。**
V47（知らなかった公演の件数）・V48（同点の割合）・V22（網ごとの興味あり率）はすべてそうである。

**反応の置き場所も無かった。** `ratings.db` にあるのは観た後の ◎○△× だけで、
観る前の「興味あり／なし」「初めて知った」「すでに持っている」を入れる表が無かった。

## 聞くのは三択（すでにチケットを持っている／興味あり／興味なし）

| 軸 | どこから来るか | 何に使うか |
|---|---|---|
| **興味あり／興味なし** | 画面のボタン | 網ごとの興味あり率（重みの更新）。興味ありは追跡の開始も兼ねる |
| **すでにチケットを持っている** | **画面のボタン（三択の 1 つ）＋ 購入確認メール。予定の正はメール** | 「観る予定」への移動（本人への返り）と、推薦の正解ラベル（興味ありより強い正） |
| **決め手**（① 理由に出た人物／② 題名・作品／③ その他） | 画面（反応が付いた行だけ） | **V24b。理由の表示を外したら何が変わるか** |
| ~~初めて知った~~ | **聞かない。撤回した**（下記） | ── |

**「すでに持っている」を二択の外に置くのをやめた**（2026-08-20・起案者の提案）。
**押す動機が本人の側にある** ──「**それが今後の観劇予定に反映されたら便利だと思ったから**」。
返りのある入力なので続く。二択のままだと置き場所が無く、[検証 021](../../docs/verification/021-first-user-reaction.md)
では集計時に「興味の上位互換だから興味なしと読むな」と後から読み替えていた。
**三択なら強さの順序（チケット保有 ＞ 興味あり ＞ 興味なし）が入力の側に入る。**

**ただし「観る予定」の正は購入確認メールである。** ボタンが受け持つのは、
**メールが残らない経路**（招待・当日窓口・人に取ってもらった）と、突き合わせを待たない近道の 2 つだけ。

**提示より前から持っていた分は、網の重みに入れない。** `presented.created_at` と
`reaction.updated_at`（またはメールの受信日）を比べれば、**「前から持っていた」と
「推薦を見てから動いた」は聞かずに割れる。** 前者を「興味ありより強い正」として数えると、
**推薦の成果でないものが効果に混ざる**（[検証 023](../../docs/verification/023-interest-rate-must-be-split.md)
で既知の当たりが興味あり率を水増ししていたのと同じ構造）。

**決め手を聞くのは、反応が付いた行だけである。** 興味なしの行に決め手は無い。
**「役に立ったか」を ◎○×で聞くのは撤回した** ── 押した後に聞けば必ず肯定が返り、
**反応そのものの言い直しになる**（起案者の指摘「「興味あり」と押した時点で、それは役に立ったと同義では？」）。

**「初めて知った」を聞くのは撤回した**（[検証 022](../../docs/verification/022-where-reactions-go.md)）。
指摘は「**以前から知っているのが表示されたから興味ありを押した場合もある。そもそもその情報は
本当に必要か**」で、実測が指摘を裏づけた ── **興味あり 8 件のうち 6 件は既知**で、興味あり率は
**既知 6/8 に対して未知 2/6**、つまり想定と逆だった。効果は「知らないものを見つけたか」ではなく
**「間に合ううちに目の前に出たか」**なので、`presented → interest → 購入メール → ◎` の連鎖で測る。
**4 段すべて既存の入力で取れるので、聞く項目は増やさない。**

**`known` の列は残す。** 上の突き合わせの根拠になった実データが入っており、消すと
撤回の理由が検証できなくなる。**ただし今後は書き込まない**（`source='chat'` の一回性の記録）。

**◎○△× とは混ぜない。** 観る前の期待（興味あり）と観た後の評価（◎）は別の量で、
混ぜると「期待どおりだったか」が測れなくなる。名簿（網 B）は ◎ だけで作る。

    python3 tools/review/feedback.py --snapshot data/review/recommend2.json --label 2026-08-20
    python3 tools/review/feedback.py --react 2026-08-20 --stage 469916 --owned 1
    python3 tools/review/feedback.py --react 2026-08-20 --stage 469916 --decider person --decider-who 松本大介
    python3 tools/review/feedback.py --report
"""

from __future__ import annotations

import argparse
import datetime
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DB = ROOT / "data" / "review" / "ratings.db"

SCHEMA = """
-- 出した一覧のスナップショット。**上書きしない**（label は「出した週」の鍵）
CREATE TABLE IF NOT EXISTS presented (
    label      TEXT NOT NULL,          -- 提示した日（YYYY-MM-DD）
    stage_id   TEXT NOT NULL,
    rank       INTEGER NOT NULL,
    title      TEXT NOT NULL,
    score      REAL NOT NULL,
    bundle     TEXT NOT NULL,          -- recommend（推定）/ favourite（申告）
    reasons    TEXT NOT NULL,          -- 理由の JSON。あとから網ごとに集計するため
    created_at TEXT NOT NULL,
    PRIMARY KEY (label, stage_id)
);
-- **実際に画面に出した一覧。** `presented` は**点を計算するたびに書かれる**ので、
-- あの表だけでは「誰かが見た一覧」と「計算しただけの一覧」を区別できない。
-- 効果の連鎖（提示 → 興味あり → 買った → ◎）の**分母はここで決まる** ──
-- 見ていない一覧を分母に数えると、興味あり率がその分だけ薄まる
CREATE TABLE IF NOT EXISTS viewed (
    label    TEXT NOT NULL,
    bundle   TEXT NOT NULL,
    first_at TEXT NOT NULL,
    source   TEXT NOT NULL,           -- screen（画面が出した）/ reaction（答えが残っている）
                                      -- / served（開いたときだけ書かれる束から復元した）
    PRIMARY KEY (label, bundle)
);
-- 反応。**観る前の評価**なので works.verdict（観た後の ◎○△×）とは別の表にする
CREATE TABLE IF NOT EXISTS reaction (
    label      TEXT NOT NULL,
    stage_id   TEXT NOT NULL,
    interest   INTEGER,                -- 1 興味あり / 0 興味なし / NULL 未回答
    known      INTEGER,                -- 1 題名を知っていた / 0 知らなかった / NULL 未回答
                                    -- **今後は書き込まない。** 2026-08-20 の 15 件だけが入る
    owned      INTEGER,                -- 1 すでにチケットを持っていた（三択のボタン、または購入メール）
    decider    TEXT,                   -- 決め手（V24b）。反応が付いた行だけ聞く
                                    --   person    理由に出た名前で決めた（誰かは decider_who）
                                    --   content   内容・題材で決めた（「ミステリーが好き」）→ 網 C
                                    --   work_same 同じ戯曲・同じ原作を前に観て良かった → **網に無い**
                                    --   work_fame 有名な作品だから観ておきたい（知名度）→ **網に無い**
                                    --   group     団体・カンパニーで決めた（「劇団☆新感線に興味がある」）
                                    --             → **網 A の申告には団体があるが、名簿（網 B）は人物単位**
                                    --   work_title 作品・戯曲そのものに興味がある（「作品4に興味がある」）
                                    --             → **前に観て良かった work_same とは違う。観たことが無くてよい**
                                    --   condition 条件（日程・劇場・値段・家からの距離・誘われた）で決めた
                                    --   undecided **これだけでは決められない。集計の分母から外す**
                                    -- **選択肢は実際の答えから作り直した**（検証 028）。
                                    -- 最初は person / work / condition の 3 つで聞いたが、
                                    -- **work が「知名度」「同じ戯曲」「内容の傾向」の
                                    -- 3 つの別の軸を飲み込んでいた。** どれも次に作るものが違う
    decider_who TEXT,                  -- 名指しされた対象（人物、または団体名）
    decider_axes TEXT,                 -- 決め手が複数の軸にまたがるときの全部（カンマ区切り）。
                                    -- **1 行に 1 つとは限らない** ──「劇団4のものは観たい。題材が題材3そう」
                                    -- は group と content の 2 軸である（2026-08-21 の回答で 3 行に出た）。
                                    -- decider には主たる軸を入れ、集計はこちらで数える
    decider_shown INTEGER,             -- 1 名指しされた決め手をシステムが理由として表示していた
                                    -- 0 表示していなかった（本人が別の経路で知っていた）
                                    -- **V24b の分子はこれが 1 の行だけである。**
                                    -- 「名前で決めている」と「システムが出した名前で決めている」は別の量で、
                                    -- 分けないと、当てていない行を成果に数え上げる
    note       TEXT,                   -- 本人の一言。**発表に引用する定性的な材料はここにしか残らない**
                                    -- **これは「興味あり」に添えた理由だけである。**
                                    -- ここから名前を拾って「お気に入り」への昇格候補を作るので
                                    -- （`tools/taguri/reasons.py`）、**見送った理由を同じ列に入れると、
                                    -- 「これが出ているから観たくない」と書いた名前が
                                    -- 登録候補として出てくる。** 別の列に分ける
    note_no    TEXT,                   -- **「興味なし」に添えた、見送った理由。**
                                    -- 「興味なし」の多くは好みの問題ではなく日程・場所・予算の
                                    -- 都合である（企画書 2 章。だからこの束は消さずに残している）が、
                                    -- **どちらだったかが記録に無いと、後から「観ればよかった」を
                                    -- 拾い直すときに見分けられない。** 昇格候補の材料には使わない
    source     TEXT NOT NULL,          -- screen（画面で押した）／ chat（会話で得た）
                                    -- ／ screen_tour（同じ作品の他会場へ及ぼした分。
                                    --   起案者の指摘・2026-08-26 ──「作品自体に
                                    --   『興味あり』を押しているのだから、代表会場に
                                    --   しか効かないのはおかしい」。**押した会場は
                                    --   screen のまま、同じ作品の他の会場へ自動で
                                    --   広げた分だけこの値にする** ── どこで得た反応か
                                    --   を混ぜて数えないため、という元の役目のまま、
                                    --   「本人が押した回数」を「効いた行数」から
                                    --   区別できるようにした
    updated_at TEXT NOT NULL,
    PRIMARY KEY (label, stage_id)
);
-- 券。**「すでに持っている」の中身、つまり「何日の回に行くのか」を持つ表である。**
--
-- `reaction.owned` は 1 か 0 しか持てないので、**公演の期間のどこに行くのかを言えない。**
-- 暦の帯は「この期間のどこかに行く」までしか表せず、**同じ公演を 2 回観る**（昼夜・
-- 初日と楽日）ことも表せなかった。**1 行 1 枚**にすれば、どちらも数の問題ではなくなる。
--
-- **鍵に time を含める。** 同じ日の昼と夜は別の回である。逆に**同じ回の 2 枚
-- （連れの分）は 1 行に畳まれる** ── 暦に置きたいのは座席の数ではなく行く回だからである。
CREATE TABLE IF NOT EXISTS ticket (
    stage_id   TEXT NOT NULL,
    date       TEXT NOT NULL,          -- YYYY-MM-DD（その回の上演日）
    time       TEXT NOT NULL DEFAULT '',  -- HH:MM。**空を許す** ── 購入確認メールに
                                       -- 時刻が無いことがあり（実測 2 件中 1 件）、
                                       -- 「日は分かるが回は分からない」を捨てないため
    source     TEXT NOT NULL,          -- mail（購入確認メールから）/ screen（本人が入れた）
    confirmed  INTEGER NOT NULL DEFAULT 0,  -- 1 本人が確定した / 0 機械が読み取ったまま
                                       -- **本人が入れた行は初めから 1 である**（入れた
                                       -- こと自体が確定である）。メールから起こした行だけが
                                       -- 0 で始まり、画面の「確定」で 1 になる ──
                                       -- 探すのは機械、確定は人、という線をここでも引く
    uid        TEXT NOT NULL DEFAULT '',  -- 購入確認メールの id。同じメールから 2 度作らない
    updated_at TEXT NOT NULL,
    PRIMARY KEY (stage_id, date, time)
);
"""


def connect(*, same_thread: bool = True) -> sqlite3.Connection:
    """**`same_thread=False` は画面の口（`tools/taguri/serve.py`）のためにある。**

    一時プロセスは要求ごとに別のスレッドで動く ── ブラウザは接続を開いたまま次の要求を
    別の接続で送るので、1 スレッドで受けると待たされて画面が固まる。**接続を跨いで使う代わりに、
    呼ぶ側が錠を掛けて直列にする**（`Server.lock`）。既定は今までどおり同一スレッド限定にする。
    """
    con = sqlite3.connect(DB, check_same_thread=same_thread)
    con.executescript(SCHEMA)
    # **既存の DB には CREATE TABLE IF NOT EXISTS が効かない**ので、足りない列だけ加える。
    have = {r[1] for r in con.execute("PRAGMA table_info(reaction)")}
    for col in ("decider TEXT", "decider_who TEXT", "note TEXT",
                "decider_axes TEXT", "decider_shown INTEGER", "note_no TEXT"):
        if col.split()[0] not in have:
            con.execute(f"ALTER TABLE reaction ADD COLUMN {col}")
    have = {r[1] for r in con.execute("PRAGMA table_info(ticket)")}
    if have and "confirmed" not in have:
        con.execute("ALTER TABLE ticket ADD COLUMN confirmed INTEGER NOT NULL DEFAULT 0")
        # **すでに入っている手入力の行は確定済みとして扱う** ── 本人が入れたものを
        # 「確定してください」と出し直すのは、同じことを 2 度聞くことになる
        con.execute("UPDATE ticket SET confirmed=1 WHERE source<>'mail'")
    backfill_viewed(con)
    con.commit()
    return con


# **開いたときにしか書かれない束。** 絞り込んだ一覧（`recommend_pref`）と、三択を押した
# 枠を埋めた 1 枚（`recommend_fill`）は、どちらも画面が要求を受けた瞬間に書いている ──
# **行があること自体が「開いた」の証拠**なので、過去の分もここから復元できる
SERVED_ONLY = ("recommend_pref", "recommend_fill")


def mark_viewed(con: sqlite3.Connection, label: str, bundle: str,
                source: str = "screen", at: str | None = None) -> None:
    """**この label のこの束を、画面に出したことを記録する。** 2 度目は何もしない。"""
    con.execute("INSERT OR IGNORE INTO viewed (label, bundle, first_at, source)"
                " VALUES (?,?,?,?)", (label, bundle, at or now(), source))


def backfill_viewed(con: sqlite3.Connection) -> None:
    """**過去の一覧のうち、証拠のあるものだけに「見た」の印を付ける。** 何度呼んでも同じ。

    **証拠は 2 つしかない。** ① その label のその束の行に反応が付いている（答えられるのは
    見たときだけである）。② 開いたときにしか書かれない束の行がある（`SERVED_ONLY`）。

    **証拠が無いものは埋めない。** 2026-08-24 の 37 回のように、開発中に計算だけした
    一覧が大半である。**「たぶん見た」で埋めると、分母を水増ししたまま数字が出る。**

    **この復元には偏りがある**（限界として書く）── ① の証拠は「1 件でも答えた一覧」しか
    拾えないので、**見たが 1 件も答えなかった一覧は落ちる。** 落ちた分は分母から抜けるため、
    **過去の興味あり率は上に出る。** 今後は画面が出した時点で印を付けるので、この偏りは
    2026-08-24 以前の分にだけ残る。
    """
    # ① **その label に反応が 1 件でもある → 推薦の一覧は出ている。**
    # `run.py` はブラウザを `/` で開き、`/` は推薦の一覧である（絞り込みは起動のあいだの
    # 設定で、既定は全国なので**最初に出るのは必ず全国の一覧**）。会話で答えた回も、
    # 一覧を貼ってから聞いている。**答えがあるなら、その一覧は本人に届いている。**
    con.execute(
        "INSERT OR IGNORE INTO viewed (label, bundle, first_at, source)"
        " SELECT r.label, 'recommend', MIN(r.updated_at), 'reaction'"
        " FROM reaction r WHERE EXISTS"
        "  (SELECT 1 FROM presented p WHERE p.label = r.label AND p.bundle = 'recommend')"
        " GROUP BY r.label")
    # ② **反応がその束の行に当たっている → その束の画面も開いている。**
    # お気に入りの新着に答えているなら、お気に入りの画面を開いたということである
    con.execute(
        "INSERT OR IGNORE INTO viewed (label, bundle, first_at, source)"
        " SELECT p.label, p.bundle, MIN(r.updated_at), 'reaction'"
        " FROM presented p JOIN reaction r"
        "   ON r.label = p.label AND r.stage_id = p.stage_id"
        " GROUP BY p.label, p.bundle")
    # ③ **開いたときにしか書かれない束は、行があること自体が証拠である。**
    ph = ",".join("?" * len(SERVED_ONLY))
    con.execute(
        "INSERT OR IGNORE INTO viewed (label, bundle, first_at, source)"
        f" SELECT label, bundle, MIN(created_at), 'served' FROM presented"
        f" WHERE bundle IN ({ph}) GROUP BY label, bundle", SERVED_ONLY)


def viewed_labels(con: sqlite3.Connection, bundle: str) -> set:
    """その束を実際に出した label。**効果を測るときの分母は、ここから作る。**"""
    return {r[0] for r in con.execute("SELECT label FROM viewed WHERE bundle=?", (bundle,))}


def now() -> str:
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def free_label(con: sqlite3.Connection, label: str) -> str:
    """**同じ label に上書きしない。** 同じ日に 2 回出したら `2026-08-20#2` にする。

    最初の実装は (label, stage_id) を主キーにして INSERT OR REPLACE していたため、
    同じ日に出し直すと**初回の順位が消えた**（実際に 1 度消した）。残すために作った表で
    上書きしていたので、目的と実装が逆だった。
    """
    base, i = label, 1
    while con.execute("SELECT 1 FROM presented WHERE label=? LIMIT 1", (label,)).fetchone():
        i += 1
        label = f"{base}#{i}"
    return label


def snapshot(con: sqlite3.Connection, path: Path, label: str) -> tuple[int, str]:
    d = json.loads(path.read_text(encoding="utf-8"))
    label = free_label(con, label)
    n = 0
    for bundle, key in (("recommend", "recommend"), ("favourite", "favourites")):
        for i, c in enumerate(d.get(key) or [], 1):
            # **網 C の理由も残す。** 網ごとの興味あり率を後から集計するので、
            # どの網で出したかが記録に無いと重みの更新に使えない（企画書 2 章）。
            reasons = {"b": c.get("why_b") or [], "a": c.get("a") or [],
                       "c": c.get("why_c") or [], "theme": c.get("theme") or []}
            con.execute("INSERT INTO presented"
                        " (label, stage_id, rank, title, score, bundle, reasons, created_at)"
                        " VALUES (?,?,?,?,?,?,?,?)",
                        (label, c["stage_id"], i, c.get("title") or "",
                         float(c.get("total") or 0), bundle,
                         json.dumps(reasons, ensure_ascii=False), now()))
            n += 1
    con.commit()
    return n, label


def react(con: sqlite3.Connection, label: str, stage_id: str, *,
          interest=None, known=None, owned=None, decider=None, decider_who=None,
          decider_axes=None, decider_shown=None, note=None, note_no=None,
          source="screen") -> None:
    """**押し直せるようにする。渡さなかった列は消さない。**

    三択は「いま本人がどの状態にいるか」であって一度きりの採点ではないので、
    **興味あり → チケットを持っている**という遷移が起こる。前の実装は INSERT OR REPLACE
    だったため、`--interest` だけで押し直すと `owned` が NULL に戻っていた。
    遷移そのものが V33・V32 の連鎖（提示 → 興味あり → 購入）の記録なので、消してはいけない。
    """
    con.execute("INSERT INTO reaction"
                " (label, stage_id, interest, known, owned, decider, decider_who,"
                "  decider_axes, decider_shown, note, note_no, source, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
                " ON CONFLICT(label, stage_id) DO UPDATE SET"
                "  interest    = COALESCE(excluded.interest, reaction.interest),"
                "  known       = COALESCE(excluded.known, reaction.known),"
                "  owned       = COALESCE(excluded.owned, reaction.owned),"
                "  decider     = COALESCE(excluded.decider, reaction.decider),"
                "  decider_who = COALESCE(excluded.decider_who, reaction.decider_who),"
                "  decider_axes = COALESCE(excluded.decider_axes, reaction.decider_axes),"
                "  decider_shown = COALESCE(excluded.decider_shown, reaction.decider_shown),"
                "  note        = COALESCE(excluded.note, reaction.note),"
                "  note_no     = COALESCE(excluded.note_no, reaction.note_no),"
                "  source      = excluded.source,"
                "  updated_at  = excluded.updated_at",
                (label, stage_id, interest, known, owned, decider, decider_who,
                 decider_axes, decider_shown, note, note_no, source, now()))
    con.commit()


def add_ticket(con: sqlite3.Connection, stage_id: str, date: str, time: str = "",
               *, source: str = "screen", uid: str = "") -> None:
    """券を 1 枚記録する。**同じ回を 2 度入れても増えない。**

    **本人が入れた行を、メールの取り込みで上書きしない** ── メールから起こした行に
    本人が時刻を足したり日を直したりしたら、そちらが確定である（探すのは機械、
    確定は人）。だから `source='mail'` の書き込みは、既にある行に触らない。

    **本人が入れた行は、その場で確定である。** メールから起こした行だけが確定前で
    始まり、画面の「確定」を押すまで 0 のままになる。**同じ回を本人が入れ直したら、
    それは確定の合図である**ので 1 に上がる（下げることはしない）。
    """
    ok = 0 if source == "mail" else 1
    con.execute("INSERT INTO ticket"
                " (stage_id, date, time, source, confirmed, uid, updated_at)"
                " VALUES (?,?,?,?,?,?,?)"
                " ON CONFLICT(stage_id, date, time) DO UPDATE SET"
                "  source     = CASE WHEN excluded.source='mail' THEN ticket.source"
                "                    ELSE excluded.source END,"
                "  confirmed  = MAX(ticket.confirmed, excluded.confirmed),"
                "  uid        = CASE WHEN excluded.uid='' THEN ticket.uid"
                "                    ELSE excluded.uid END,"
                "  updated_at = excluded.updated_at",
                (str(stage_id), date, time or "", source, ok, uid or "", now()))
    con.commit()


def confirm_ticket(con: sqlite3.Connection, stage_id: str, date: str,
                   time: str = "") -> int:
    """機械が読み取った 1 枚を、本人が確定する。**出どころは書き替えない** ──
    どこから来た値なのかは、確定したあとも記録として要る。
    """
    n = con.execute("UPDATE ticket SET confirmed=1, updated_at=?"
                    " WHERE stage_id=? AND date=? AND time=?",
                    (now(), str(stage_id), date, time or "")).rowcount
    con.commit()
    return n


def del_ticket(con: sqlite3.Connection, stage_id: str, date: str, time: str = "") -> int:
    """券を 1 枚取り消す。**取り消せることが、入れられることと同じだけ要る** ──
    日を間違えて入れたときに直す道が無いと、暦に嘘の点が残る。
    """
    n = con.execute("DELETE FROM ticket WHERE stage_id=? AND date=? AND time=?",
                    (str(stage_id), date, time or "")).rowcount
    con.commit()
    return n


def tickets(con: sqlite3.Connection) -> dict[str, list[dict]]:
    """公演の id → 持っている券（日の早い順）。**1 公演に何枚でも入る。**"""
    out: dict[str, list[dict]] = {}
    for stage_id, date, time, source, confirmed, uid in con.execute(
            "SELECT stage_id, date, time, source, confirmed, uid FROM ticket"
            " ORDER BY date, time"):
        out.setdefault(str(stage_id), []).append(
            {"date": date, "time": time or "", "source": source,
             "confirmed": int(confirmed or 0), "uid": uid or ""})
    return out


def reactions(con: sqlite3.Connection) -> dict[str, dict]:
    """公演ごとに、これまでに得た反応をまとめて返す。

    **鍵は label ではなく stage_id である。** 反応は「その週に出したもの」に対して付くが、
    抑制は**公演そのもの**に効かなければならない ── 先週「興味なし」と答えた公演が、
    今週また同じ順位で出るのを止めるのが目的だからである（[検証 022](../../docs/verification/022-where-reactions-go.md)）。

    **同じ公演に複数回の反応があれば、新しいほうを採る。** 興味は変わりうる。

    **題名も返す。** 抑制を stage_id だけで掛けると、**同じ作品のツアーの別会場が別の
    stage_id を持つため、外したはずの公演が同じ枠に戻ってくる**（検証 026 で実際に
    フタマツヅキとミス・サイゴンが別 ID で復活した）。呼ぶ側が作品単位に畳めるようにする。
    """
    out: dict[str, dict] = {}
    for stage_id, interest, owned, title in con.execute(
            "SELECT r.stage_id, r.interest, r.owned,"
            " (SELECT p.title FROM presented p WHERE p.stage_id = r.stage_id LIMIT 1)"
            " FROM reaction r ORDER BY r.updated_at"):
        d = out.setdefault(str(stage_id), {})
        if interest is not None:
            d["interest"] = int(interest)
        if owned is not None:
            d["owned"] = int(owned)
        d["title"] = title or ""
    return out


def missed_fields(con: sqlite3.Connection) -> list[dict]:
    """「観ればよかった」に登録した公演の、調べ済みのクレジット（役職・出演者）の並び。

    起案者の指示（2026-08-26）──「『観ればよかった』で挙がった人名は『興味あり』の
    ボタンを押した扱いと同じにして、推薦に反映させて」。**見逃して悔しいと自分で
    登録した公演は、「興味あり」と同じ「もっと知りたい」という意思表示である。**

    **調べが済んでいない分（`fields_json` が空）は静かに飛ばす。** 登録した直後は
    まだ演者を調べている途中で、材料が無いだけなので、失敗として扱わない。
    """
    try:
        rows = con.execute(
            "SELECT fields_json FROM missed WHERE fields_json IS NOT NULL").fetchall()
    except sqlite3.OperationalError:
        return []
    out = []
    for (fj,) in rows:
        if not fj:
            continue
        try:
            f = json.loads(fj)
        except (TypeError, ValueError):
            continue
        if f:
            out.append(f)
    return out


def _interest(con: sqlite3.Connection, label: str) -> int:
    """興味ありの**押した回数**。

    **同じ作品の他会場へ広げた行（`source='screen_tour'`）は数えない**（起案者の
    指摘・2026-08-26 で `on_react` が反応を作品単位に広げるようになった分）。
    1 回押すとツアーの会場数ぶん行が増えるので、そのまま数えると押した回数より
    多く出る ── **回数は「押した回数」を答える値である。**
    """
    return con.execute(
        "SELECT COUNT(*) FROM reaction"
        " WHERE label=? AND interest=1 AND source != 'screen_tour'",
        (label,)).fetchone()[0]


def report(con: sqlite3.Connection) -> None:
    # **計算しただけの一覧と、実際に出した一覧を分けて出す。**（2026-08-24）
    # 前は `presented` の label を全部並べていたが、**開発中に計算した回まで同じ顔で
    # 並ぶ**ので、どれが本当の提示なのか読めなかった。**効果の分母は「出した分」である。**
    tot = list(con.execute(
        "SELECT bundle, COUNT(DISTINCT label), COUNT(*) FROM presented GROUP BY bundle"))
    print("提示の記録")
    for bundle, n_lab, n_row in tot:
        seen = viewed_labels(con, bundle)
        if seen:
            ph = ",".join("?" * len(seen))
            n_seen = con.execute(
                f"SELECT COUNT(*) FROM presented WHERE bundle=? AND label IN ({ph})",
                (bundle, *seen)).fetchone()[0]
        else:
            n_seen = 0
        print(f"  {bundle}: 計算 {n_lab} 回・{n_row} 行 ／ "
              f"**画面に出した {len(seen)} 回・{n_seen} 行**"
              + (f"（残り {n_lab - len(seen)} 回は計算しただけ ── 分母から外す）"
                 if n_lab > len(seen) else ""))
    print("\n出した一覧（label ごと）:")
    for label, bundle, first_at, src in con.execute(
            "SELECT label, bundle, first_at, source FROM viewed ORDER BY first_at, label"):
        n = con.execute("SELECT COUNT(*) FROM presented WHERE label=? AND bundle=?",
                        (label, bundle)).fetchone()[0]
        note = {"screen": "画面が記録", "reaction": "答えから復元",
                "served": "開いたときだけ書かれる束から復元"}.get(src, src)
        print(f"  {label} {bundle}: {n} 件（{note}・{first_at}）")
    # **`screen_tour`（同じ作品の他会場へ広げた行）は「回答」から外す。** 押したのは
    # 1 回でも、ツアーの会場数ぶん行が増えるので、そのまま数えると回答した回数より
    # 多く出てしまう ── ここでも `_interest` と同じ理由で分ける
    rows = list(con.execute(
        "SELECT r.label, SUM(r.source != 'screen_tour'), SUM(r.known=0),"
        " SUM(r.owned=1 AND r.source != 'screen_tour'), SUM(r.source = 'screen_tour')"
        " FROM reaction r GROUP BY r.label ORDER BY r.label"))
    if not rows:
        print("反応の記録はまだ無い")
        return
    print("\n反応:")
    for label, n, unknown, owned, tour in rows:
        print(f"  {label}: 回答 {n} 件／興味あり {_interest(con, label)}"
              f"／すでに持っていた {owned or 0}"
              + (f"（参考: 題名を知らなかった {unknown} ── この軸は集めていない）" if unknown else "")
              + (f"（同じ作品の他会場へ広げた行が別に {tour} 件ある ── 上の数には含まない）"
                 if tour else ""))
    dec = list(con.execute(
        "SELECT COALESCE(decider,'未回答'), COUNT(*) FROM reaction"
        " WHERE interest=1 OR owned=1 GROUP BY 1 ORDER BY 2 DESC"))
    # **undecided は「決められない」であって「名前で決めなかった」ではない。**
    # 表示が足りないことの記録なので、率を出すときは分母から外す（検証 021 の指摘 1）。
    if dec:
        # **分母は反応が付いた行だけ。** 興味なしの行に決め手は無い（V24b）。
        tot = sum(n for _, n in dec)
        s_ = "／".join(f"{k} {n}" for k, n in dec)
        print(f"\n決め手（V24b・反応が付いた {tot} 件）: {s_}")
    print("\n連鎖（提示 → 興味あり → 買った → ◎）で測る。**買った以降は購入確認メールの"
          "判定と抽出が 2026-04-08 で止まっているため、まだ数えられない**（検証 022）")
    # **網ごとの興味あり率は、まだ出さない。** 理由は下記
    nets = set()
    for (rj,) in con.execute("SELECT reasons FROM presented WHERE bundle='recommend'"):
        for _, role, _p, _n in (json.loads(rj).get("b") or []):
            nets.add(role)
    print(f"\n理由に使われた役職 {len(nets)} 種。**網ごとの興味あり率はまだ集計しない** ── "
          "動いているのは網 B だけで、網の重みは網どうしの比較で決まるため")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot", type=Path, help="recommend2.json を読んで保存する")
    ap.add_argument("--label", default=datetime.date.today().isoformat())
    ap.add_argument("--react", metavar="LABEL")
    ap.add_argument("--stage")
    ap.add_argument("--interest", type=int)
    ap.add_argument("--known", type=int)
    ap.add_argument("--owned", type=int)
    ap.add_argument("--decider",
                    choices=("person", "content", "work_same", "work_fame",
                             "group", "work_title", "condition", "undecided"),
                    help="決め手（V24b）。反応が付いた行だけ。undecided は分母から外す")
    ap.add_argument("--decider-who", help="--decider person のとき、名指しされた人物")
    ap.add_argument("--decider-axes",
                    help="決め手が複数の軸にまたがるときの全部（カンマ区切り）")
    ap.add_argument("--decider-shown", type=int,
                    help="1 その決め手をシステムが表示していた／0 表示していなかった")
    ap.add_argument("--note", help="本人の一言（発表に引用する材料）")
    ap.add_argument("--source", default="screen")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()

    con = connect()
    if a.snapshot:
        n, used = snapshot(con, a.snapshot, a.label)
        print(f"{n} 件を presented に保存（label={used}）")
    if a.react:
        if not a.stage:
            print("--stage が要る")
            return 2
        react(con, a.react, a.stage, interest=a.interest, known=a.known,
              owned=a.owned, decider=a.decider, decider_who=a.decider_who,
              decider_axes=a.decider_axes, decider_shown=a.decider_shown,
              note=a.note, source=a.source)
        print(f"記録: {a.react} / {a.stage}")
    if a.report or not (a.snapshot or a.react):
        report(con)
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
