#!/usr/bin/env python3
"""網 C の軸を 3 通りに組んで比べる（検証 040 追記 3）── 事実／感情／両方。

項目名は**日本劇作家協会の戯曲デジタルアーカイブが公開している 34 ジャンル**から借りる。
上演する側の項目（パブリックドメイン・方言活用・高校演劇など）は落とし、**足すことはしない**
（起案者の判断 ──「借りるのは良い。足すのは適宜今後の公演を分析し検討していかなければならない」）。

軸を混ぜて提案していたのを分けたのが追記 1、感情の軸を外す理由が消えたのが追記 2 である。
**候補側には感想もクチコミも無い**（初日前に限ると決めている）ので、感情の軸も
あらすじからの推定しか道が無い。

**版を固定して読む。** `themes.jsonl` は版を上げるときに全件を引き直す運用なので、
測るときは 1 つの版だけを読む（`--pv`）。混ざった状態で測ると再現しない。

    python3 tools/review/net_c_axes.py --axis fact --pv c2
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure_nets as M                                    # noqa: E402
import net_c as C                                           # noqa: E402

THEMES = ROOT / "data" / "credits" / "themes.jsonl"
EXCLUDED = set(json.loads((ROOT / "data/credits/theme_groups.json").read_text(encoding="utf-8"))["excluded"])

FACT = {
 "恋愛": "恋愛 悲恋 愛 愛人 不倫 三角関係 身分違い 心中 執着 欲望 舞踏会",
 "ミステリー": "ミステリー 推理 探偵 探偵事務所 殺人事件 殺人 犯罪 事件 密室 怪盗 泥棒 スパイ"
              " 失踪 失踪事件 冤罪 法廷 法律事務所 毒 秘密 嘘 追跡劇 監獄 陰謀論 闇バイト 都市伝説 人体実験",
 "SF・近未来": "SF 近未来 宇宙 宇宙船 タイムスリップ 時間旅行 AI ロボット テクノロジー 題材3"
               " ディストピア 終末 終末世界 不老不死 入れ替わり 天文台 記憶喪失",
 "ファンタジー": "ファンタジー 幻想 幻想的 異世界 異世界転生 魔法 魔法の世界 妖精 妖怪 神話 伝説"
                " 童話 昔話 御伽噺 寓話 不思議の国 変身 天使 王国 王宮 宮廷 冒険 陰陽師",
 "戦記": "戦争 戦地 戦後 特攻隊 合戦 戦国時代 武将 侵略 冷戦 ソ連 赤狩り 共産主義"
        " ユダヤ人居住区 植民地時代 大恐慌 仇討ち 建国 任侠",
 "政治・社会問題": "政治 選挙 会議 権力 独裁国家 粛清 階級社会 貴族社会 貧困 労働 失業 借金"
                  " 少子化 障害 社交不安障害 移民 移住 環境 震災 報道 薬物 宗教 反出生主義 社会派"
                  " 社会風刺 風刺 介護 認知症 福祉施設 闇市 対立 女性 闘病 病院 サナトリウム",
 "時代劇": "時代物 時代劇 江戸時代 江戸 明治時代 昭和 昭和時代 幕末 史劇 長屋 茶屋 寺 神社 村 農村",
 "現代劇": "現代 日常 職場 会社 企業 仕事 団地 住宅街 アパート 商店街 喫茶店 スナック バー"
          " 居酒屋 レストラン スーパーマーケット 理容室 同居 実家 同窓会 街 地方都市 港町 漁師町"
          " 離島 製鉄所 ホテル 客船 屋敷 邸宅 古民家 路地 偲ぶ会 葬儀屋 中年の危機",
 "学園モノ": "学校 高校 青春 不登校 寄宿舎 全寮制学校 児童館 子ども 子供向け",
 "評伝劇": "評伝劇 伝記 作家",
 "エロティック": "エロティック",
 "多様性": "多様性",
}
EMO = {
 "悲劇": "悲劇 悲喜劇 死別 死 生と死 苦悩 哀愁 切なさ 孤独 運命 トラウマ 狂気",
 "喜劇": "コメディ 喜劇 ユーモア ユーモラス 滑稽 娯楽 ブラックコメディ",
 "人情劇": "人情 人情劇 人助け ハートフル 絆 祝福 祝祭 希望 再生 救済",
 "ホラー": "ホラー 怪談 怪奇 オカルト ゾンビ 吸血鬼 幽霊 呪い 冥界 廃墟",
 "泣ける": "泣ける 感動",
 "ナンセンス": "ナンセンス 不条理 不条理劇 寓話的",
 "お茶の間": "お茶の間",
}


def build(d: dict) -> dict[str, str]:
    m: dict[str, str] = {}
    for g, txt in d.items():
        for w in txt.split():
            if w in EXCLUDED or C.nz(w) in m:
                continue
            m[C.nz(w)] = g
    return m


def load_themes(pv: str, pv_cand: str = "") -> dict:
    """**版を 1 つに絞って読む。** 混ざった状態で測ると再現しない。

    **側ごとに版が違うと、絞った側だけが空になる。** 実際に起きた ── 候補側だけを
    c4（題名を渡す版・[検証 042](../../docs/verification/042-synopsis-prompt.md)）で
    引き直したので、`--pv c2` では候補側が 1 件も読めない。**候補側の列が黙って 0 になる**
    ので、**空になった側を名指しで警告する。**

    **側ごとに版を指定できるようにした**（`--pv-cand`）。学習側の持ち上がりの表を候補側に
    当てるので、版が違えば語彙のずれがそのまま件数に出る。**ずれ自体も測る対象である。**
    """
    out = {}
    seen: dict[str, set] = {}
    for l in THEMES.read_text(encoding="utf-8").split("\n"):
        if not l.strip():
            continue
        r = json.loads(l)
        seen.setdefault(r["side"], set()).add(r.get("prompt_version"))
        want = (pv_cand or pv) if r["side"] == "candidate" else pv
        if want and r.get("prompt_version") != want:
            continue
        out[(r["side"], str(r["id"]))] = r
    for side, vs in seen.items():
        want = (pv_cand or pv) if side == "candidate" else pv
        if want and want not in vs:
            print(f"    ⚠ {side} 側に版 {want} の行が無い（あるのは {'・'.join(sorted(map(str, vs)))}）。"
                  f"**この側は 0 件として数えられる。**")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--axis", choices=["fact", "emo", "both", "emo2", "both2"], default="fact")
    ap.add_argument("--pv", default="c2", help="学習側で読む prompt_version")
    ap.add_argument("--pv-cand", default="", help="候補側で読む prompt_version（既定は --pv と同じ）")
    a = ap.parse_args()
    table = {"fact": FACT, "emo": EMO, "both": {**FACT, **EMO},
             "emo2": EMO, "both2": {**FACT, **EMO}}[a.axis]
    W2G = build(table)
    # emo2 / both2 は、あらすじを聞き直して付けた感情ラベル（版 e1）を使う。
    # 既存の抽出は感情を聞いていないので、語からの写しでは 7 項目のうち 3 項目が 0 件だった。
    EMOF = ROOT / "data" / "credits" / "emotions.jsonl"
    emo_lab: dict[str, list[str]] = {}
    if a.axis in ("emo2", "both2"):
        for l in EMOF.read_text(encoding="utf-8").split("\n"):
            if not l.strip():
                continue
            r = json.loads(l)
            emo_lab[str(r["id"])] = sorted({x["genre"] for x in (r.get("labels") or [])})

    def axis_words(row: dict | None) -> list[str]:
        if not row:
            return []
        if a.axis == "emo2":
            return list(emo_lab.get(str(row.get("id")), []))
        skip = {C.nz(w) for w in C.DECLARED_THEME if C.nz(w)}
        out = set()
        for e in row.get("elements", []):
            w = C.nz(e.get("word", ""))
            if not w or w in EXCLUDED or any(s in w or w in s for s in skip):
                continue
            g = W2G.get(w)
            if g:
                out.add(g)
        if a.axis == "both2":
            out |= set(emo_lab.get(str(row.get("id")), []))
        return sorted(out)

    C.words = axis_words
    themes = load_themes(a.pv, a.pv_cand)
    rated = M.load_rated()
    pos = lambda v: 1.0 if v == "◎" else 0.0                # noqa: E731
    have = [r for r in rated if axis_words(themes.get(("rated", r["key"])))]
    n_pos = sum(1 for r in have if pos(r["verdict"]))
    print(f"■ 軸 = {a.axis}（{len(table)} 項目・割当語 {len(W2G)}）／版 学習側 {a.pv}・候補側 {a.pv_cand or a.pv}")
    print(f"   学習側で枠が付いたのは {len(have)}/{len(rated)} 作品（◎ {n_pos} 件）")

    cand = [(k[1], v) for k, v in themes.items() if k[0] == "candidate"]
    cnt_c: collections.Counter = collections.Counter()
    for _, v in cand:
        for g in axis_words(v):
            cnt_c[g] += 1
    lift = C.build_lift(rated, themes, pos)
    print("   ① 項目ごと（n・◎・差・候補側）")
    rows = []
    for g in table:
        n = sum(1 for r in have if g in axis_words(themes.get(("rated", r["key"]))))
        o = sum(1 for r in have if g in axis_words(themes.get(("rated", r["key"]))) and pos(r["verdict"]))
        raw = (o / max(n_pos, 1) - n / len(have)) if n else None
        rows.append((g, n, o, raw, cnt_c.get(g, 0)))
    for g, n, o, raw, nc in sorted(rows, key=lambda r: -(r[3] if r[3] is not None else -9)):
        s = f"{raw:+.3f}" if raw is not None else "  ──  "
        print(f"      {g:<12} n={n:<3} ◎={o:<3} 差 {s}  候補 {nc:>4}")

    pairs_b, pairs_bc, pairs_c = [], [], []
    for i, r in enumerate(have):
        rest = have[:i] + have[i + 1:]
        lf = C.build_lift(rest, themes, pos)
        rest_all = [x for x in rated if x["key"] != r["key"]]
        roster = M.build_roster(rest_all, pos)
        base = sum(float(pos(x["verdict"])) for x in rest_all) / len(rest_all)
        b = M.score(r, roster, base, by_role=True)
        c, _ = C.strength(axis_words(themes.get(("rated", r["key"]))), lf)
        y = bool(pos(r["verdict"]))
        pairs_b.append((b, y)); pairs_bc.append((b + c, y)); pairs_c.append((c, y))
    print(f"   ② C だけ {M.auc(pairs_c)} ／ B だけ {M.auc(pairs_b)} ／ B+C {M.auc(pairs_bc)}（n={len(have)}）")

    import random
    rnd = random.Random(20260821)
    diffs, cs = [], []
    for _ in range(40):
        samp = [have[rnd.randrange(len(have))] for _ in range(len(have))]
        keys = {r["key"] for r in samp}
        if len({bool(pos(r["verdict"])) for r in samp}) < 2:
            continue
        lf = C.build_lift(samp, themes, pos)
        pb, pbc, pc = [], [], []
        for r in have:
            if r["key"] in keys:
                continue
            rest_all = [x for x in rated if x["key"] not in keys and x["key"] != r["key"]] or rated
            roster = M.build_roster(rest_all, pos)
            base2 = sum(float(pos(x["verdict"])) for x in rest_all) / len(rest_all)
            b = M.score(r, roster, base2, by_role=True)
            c, _ = C.strength(axis_words(themes.get(("rated", r["key"]))), lf)
            y = bool(pos(r["verdict"]))
            pb.append((b, y)); pbc.append((b + c, y)); pc.append((c, y))
        ab, abc, ac = M.auc(pb), M.auc(pbc), M.auc(pc)
        if None in (ab, abc, ac):
            continue
        diffs.append(abc - ab); cs.append(ac)
    if diffs:
        f = lambda xs: (sum(xs) / len(xs),                    # noqa: E731
                        (sum((x - sum(xs) / len(xs)) ** 2 for x in xs) / max(len(xs) - 1, 1)) ** 0.5)
        cm, csd = f(cs); dm, dsd = f(diffs)
        print(f"   取り直し {len(diffs)} 回 ── C だけ {cm:.3f} ± {csd:.3f}／"
              f"B+C − B = {dm:+.3f} ± {dsd:.3f}（上がった回 {sum(1 for d in diffs if d > 0)}/{len(diffs)}）")
    n_syn = sum(1 for _, v in cand if v.get("synopsis"))
    n_g = sum(1 for _, v in cand if axis_words(v))
    n_s = sum(1 for _, v in cand if C.strength(axis_words(v), lift)[0] > 0)
    print(f"   ③ 候補 {len(cand)} 件 ── あらすじ {n_syn} 件／枠が付いた {n_g} 件／強さが正 {n_s} 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
