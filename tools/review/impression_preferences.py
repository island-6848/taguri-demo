"""感想で明示された特徴への好みを、利用者の推薦に反映する（外部送信なし）。

公演に登録済みの要素だけを評価対象にする。作品全体の評価から全要素への
好き嫌いを推測しない。プロフィールは現在の記録から毎回作り直し、編集・削除を反映する。
"""
from __future__ import annotations

import re
import unicodedata

PRIOR = 3
WEIGHT = 0.75
TOP_N = 3

# 同じ特徴に限って表記を揃える。「恋愛」と「恋愛が多い」などは統合しない。
ALIASES = (
    ("コメディ", "喜劇", "コメディー"),
    ("恋愛", "ラブストーリー"),
    ("会話の掛け合い", "会話劇", "会話中心", "会話の応酬"),
    ("身体表現", "フィジカルシアター"),
    ("観客参加", "観客参加型"),
    ("解釈を観客に委ねる結末", "解釈を観客に委ねる", "開かれた結末"),
)


def norm(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text or "")).lower()


def canonical(word: str) -> str:
    w = norm(word)
    for aliases in ALIASES:
        if w in map(norm, aliases):
            return norm(aliases[0])
    return w


def features(elements: list) -> dict[str, str]:
    """正規化した特徴 → 公演に登録された表示名。部分一致で別の特徴へ広げない。"""
    out = {}
    for element in elements:
        word = element.get("word", "") if isinstance(element, dict) else element
        if isinstance(word, str) and len(norm(word)) >= 2:
            out.setdefault(canonical(word), word)
    return out


# 否定された肯定語を先に取ることで、「面白くない」の「面白」を加点しない。
_EVALUATION = re.compile(
    r"(?P<negative>好き(?:では|じゃ|で)?な(?:い|かった)|"
    r"好み(?:では|じゃ)な(?:い|かった)|"
    r"面白くな(?:い|かった)|楽しくな(?:い|かった)|楽しめな(?:い|かった)|"
    r"よくな(?:い|かった)|良くな(?:い|かった)|"
    r"苦手(?:だった|です)?|嫌い(?:だった|です)?|つまらな(?:い|かった)|"
    r"退屈(?:だった|です)?|合わな(?:い|かった)|多すぎ(?:る|た)|"
    r"物足りな(?:い|かった))"
    r"|(?P<weak>悪くな(?:い|かった))"
    r"|(?P<positive>好き(?:だった|です)?|好み(?:だった|です)?|"
    r"面白(?:い|かった)|楽し(?:い|かった|めた)|よかった|良かった|"
    r"最高(?:だった|です)?|魅力的|心地よ(?:い|かった)|刺さ(?:る|った))"
)
_X_MARK = re.compile(r"\n*\[X (?:\d{4}-\d{2}-\d{2})?\] https://x\.com/[A-Za-z0-9_]{1,15}/status/\d{1,25}\s*\Z")
_SPLIT = re.compile(r"[。！？!?\n、,;；]|けれど(?:も)?|けど|しかし|でも|一方(?:で)?|だが|ですが")
_UNCERTAIN = re.compile(r"かもしれ|とは(?:言え|いえ|限ら)|わけ(?:では|じゃ)|ではなく|じゃなく|とは思わ")
_REPORTED = re.compile(r"[」』](?:と|って)(?:言|話|語|叫)|(?:という|と言う)(?:台詞|セリフ)")
# 他の対象の評価が途中に入っていたら結び付けない（「家族の話で演技がよかった」等）。
_BRIDGE = re.compile(r"(?:は|が|を|も|に|の|って|という|として|ところ|"
                     r"描写|描き方|描かれ方|物語|話|テーマ|題材|表現|関係|要素|部分|"
                     r"とても|すごく|凄く|本当に|とにかく|かなり|特に|非常に|"
                     r"多くて|多く|中心で|中心の|あって|ある|描かれていて)*")


def extract(note: str, elements: list) -> list[dict]:
    """同じ節で特徴に続く明確な評価だけを結び付ける。曖昧な文は保留する。"""
    vocabulary = features(elements)
    signals = []
    for raw in _SPLIT.split(note or ""):
        clause = norm(raw)
        if not clause or _REPORTED.search(clause):
            continue
        mentions = []
        for key, label in vocabulary.items():
            aliases = next((a for a in ALIASES if canonical(a[0]) == key), (label,))
            for alias in set(map(norm, aliases)) | {norm(label)}:
                for match in re.finditer(re.escape(alias), clause):
                    mentions.append((match.start(), match.end(), key))
        # 同じ箇所の「観客参加」と「観客参加型」などは、最長の一致だけを採る。
        mentions.sort(key=lambda m: (m[0], -(m[1] - m[0]), m[2]))
        chosen = []
        for mention in mentions:
            if not any(mention[0] < m[1] and m[0] < mention[1] for m in chosen):
                chosen.append(mention)
        for i, (start, end, key) in enumerate(chosen):
            stop = chosen[i + 1][0] if i + 1 < len(chosen) else len(clause)
            tail = clause[end:stop]
            # 遠くの評価や推量を特徴への好みと決めつけない。
            if _UNCERTAIN.search(tail):
                continue
            evaluations = list(_EVALUATION.finditer(tail))
            if not evaluations or evaluations[0].start() > 16:
                continue
            if not _BRIDGE.fullmatch(tail[:evaluations[0].start()]):
                continue
            if any(re.match(r"(?:では|じゃ|で)な(?:い|かった)", tail[m.end():])
                   for m in evaluations):
                continue  # 「苦手ではない」「最高ではない」は好みの方向を保留する。
            values = {(-1.0 if m.lastgroup == "negative" else
                       0.5 if m.lastgroup == "weak" else 1.0) for m in evaluations}
            if len(values) != 1:
                continue
            quote = raw.strip()
            if len(quote) > 160:
                quote = quote[:160] + "…"
            signals.append({"feature": key, "label": vocabulary[key],
                            "value": values.pop(), "quote": quote})
    return signals


def build_profile(works: list[dict], themes: dict) -> dict[str, dict]:
    """1 作品・1 特徴につき 1 票。見ていない作品・未来の記録は呼び出し側でも除く。"""
    votes: dict[str, list] = {}
    seen = set()
    for work in works:
        key = str(work.get("work_key") or work.get("key") or "")
        if not key or key in seen or work.get("unseen"):
            continue
        seen.add(key)
        # X のポストから取り込んだ感想の出どころの行（cloudflare/src/x-post.js）は読まない
        note = _X_MARK.sub("", work.get("note_impression") or "")
        if not note.strip():
            continue
        # rated 要素は元の作品、公演へのリンクは手入力の記録にも使える。
        row = themes.get(("rated", key)) or themes.get(("candidate", str(work.get("stage_id") or ""))) or {}
        per_work: dict[str, list] = {}
        for signal in extract(note, row.get("elements") or []):
            per_work.setdefault(signal["feature"], []).append(signal)
        for feature, signals in per_work.items():
            values = {s["value"] for s in signals}
            if any(v > 0 for v in values) and any(v < 0 for v in values):
                continue  # 同じ特徴について好評と不評が混在する作品は保留。
            signal = signals[-1]
            votes.setdefault(feature, []).append({
                **signal, "value": sum(values) / len(values), "work_key": key,
                "title": work.get("title") or "", "date": work.get("first_date") or "",
            })
    profile = {}
    for feature, evidence in votes.items():
        evidence.sort(key=lambda e: (e["date"], e["work_key"]), reverse=True)
        profile[feature] = {"weight": sum(e["value"] for e in evidence) / (len(evidence) + PRIOR),
                            "count": len(evidence), "evidence": evidence}
    return profile


def score(elements: list, profile: dict) -> tuple[float, list[dict]]:
    parts = []
    for feature, label in features(elements).items():
        p = profile.get(feature)
        if not p or not p["weight"]:
            continue
        sign = 1 if p["weight"] > 0 else -1
        evidence = next(e for e in p["evidence"] if e["value"] * sign > 0)
        parts.append({"feature": feature, "label": label, "value": p["weight"],
                      "count": p["count"], "evidence": dict(evidence)})
    parts.sort(key=lambda p: (-abs(p["value"]), p["feature"]))
    parts = parts[:TOP_N]
    # 特徴が多い公演が有利にならないよう、固定の上限で平均し補正を抑える。
    adjustment = round(WEIGHT * sum(p["value"] for p in parts) / TOP_N, 6)
    return adjustment, parts


def rerank(data: dict, profile: dict, *, multiplier: float = 1.0, top: int = 15) -> dict:
    """現在の利用者だけに補正を適用。共有の一覧・お気に入り・回答済みの束は動かさない。"""
    out = dict(data)
    ranked, unscored = [], []
    for bucket in ("ranked", "unscored"):
        for original in data.get(bucket) or []:
            row = dict(original)
            adjustment, why = score(row.get("themes") or [], profile) if multiplier > 0 else (0.0, [])
            adjustment = round(adjustment * multiplier, 6)
            row["impression_score"], row["why_impression"] = adjustment, why
            row["impression_base_total"] = float(row.get("impression_base_total", row.get("total")) or 0)
            row["total"] = round(row["impression_base_total"] + adjustment, 4)
            row["preference_rank"] = round(float(row.get("strong") or 0) + adjustment, 6)
            if bucket == "ranked" or adjustment > 0:
                ranked.append(row)
            else:
                unscored.append(row)
    ranked.sort(key=lambda r: (-r["preference_rank"], -float(r.get("s") or 0)))
    out["ranked"], out["unscored"] = ranked, unscored
    out["recommend"] = ranked[:top]
    return out
