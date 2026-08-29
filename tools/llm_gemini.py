#!/usr/bin/env python3
"""LLM を「部品」として呼ぶ、共通の口（Gemini API）。

## なぜこれを作ったか

これまでは `claude` CLI をサブプロセスとして呼ぶコードが、あらすじ抽出・感情抽出・
購入確認メールの判定など 6 箇所にそれぞれ別々に書かれていた（`subprocess.run(["claude",
"-p", ...])` → 出力を正規表現で `[...]` の形に切り出す → `json.loads`、を 6 回重複）。

起案者の指摘（2026-08-27）──「それってコスト面でもセキュリティ面でもまずいのでは？
gemini apiに変えたい」。**`claude` CLI は対話用セッションと同じ枠・同じログイン状態を
使っており、専用の課金経路も専用の資格情報も持たなかった。** バッチ処理の認証を
対話用 CLI のログイン状態に依存させない、という指摘は妥当なので、専用の API キーに
切り離す。あわせて、6 箇所で重複していた「呼ぶ・出力を切り出す・JSON にする」を
ここ 1 か所にまとめる。

## 標準ライブラリだけで動かす

`tools/README.md` の方針（環境が変わっても壊れないよう、何も入れずに動く）をここでも
守る。Gemini 公式 SDK（`google-genai`）は pip install が要るので使わず、**REST API を
`urllib` で直に叩く。**

## 鍵の置き場所（`llm-api` スキルの守り 1）

**リポジトリには置かない。** 環境変数 `GEMINI_API_KEY`、無ければ
`~/.config/taguri/gemini_api_key.txt`（リポジトリの外）を読む。どちらも無ければ
呼び出しをやめて `LLMError` を出す（無言で空を返さない）。

## 構造化出力を使う（`llm-api` スキルの守り 3）

`claude` CLI の時代は「自由文の出力から `[...]` を正規表現で探す」という当て推量を
していた。Gemini は JSON Schema を強制する機能（`responseSchema`）を持つので、
**呼び出し側が期待する形をスキーマとして渡し、崩れた出力そのものを起こさせない。**
入出力の型を固定する設計は担い手を替えても移せる、というスキルの言葉のとおりである。

## 安全フィルタは「見つからなかった」と混ぜない（`llm-api` スキルの守り 4）

演劇のあらすじは暴力・性的な題材で安全フィルタに当たることがある。ここで
`SafetyBlocked` を投げて区別し、呼び出し側が「0 件見つかった」と取り違えないように
する。**429（枠の上限）は指数バックオフで待つ。**

## 版を記録する（`llm-api` スキルの守り 3）

`ask()` は実際に応答したモデルの版（`modelVersion`）を返り値に含める。**自動更新
される別名（`gemini-2.5-flash` のような tier 名）を呼ぶ側の定数にはするが、
抽出した行には API が返した版をそのまま記録させる** ── 別名の中身が将来変わっても、
どの版で抽出したかは行に残る。

## 月間の呼び出し上限（#000008・2026-08-29）

**就活向けデモをRenderで公開するにあたり、外部から誰でも触れる画面から生きたAPIを
叩くようになる。** これまでは起案者本人しか操作しないので実質的な呼び出し回数の
上限が無かったが、不特定多数が触れる状態では費用が青天井になりうる
（[セキュリティ規約 O6](../docs/000007-taguri-security-rules.md)で決めていた
「月間の支払い上限」が、ここで初めて実際に必要になった）。

`GEMINI_MAX_CALLS_PER_MONTH`（環境変数、既定300）を超えたら、実際に呼ぶ前に
`BudgetExceeded`を投げて止める。カウントは`~/.config/taguri/gemini_budget.json`に
`{年月: 回数}`で持つ ── プロバイダ側の予算アラート（Google Cloud Console側で別途
設定する運用上の約束）と二重に守る位置づけで、**アプリ側はこちらが確実に動く砦**
である。
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

# **既定モデル。** 起案者が選んだ Gemini 2.5 Flash（2026-08-26 ── コストと精度の
# バランスで、部品としての変換作業には上位モデルの推論力は要らないという判断）。
# ここでは tier の別名だが、`ask()` が返すメタ情報の `model_version` に
# 実際に応答した版（`modelVersion`）を呼び出し側が記録することで、別名の
# 中身が変わっても抽出時点の版は残る。
# **2026-08-29、`gemini-2.5-flash`がAPI側で廃止され、404を返すようになった**
# （エラーメッセージが`gemini-3.6-flash`への移行を明示的に案内していた）ため、
# 動作確認のうえ切り替えた。判断基準（コストと精度のバランス）自体は変わらない。
MODEL = "gemini-3.6-flash"

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_KEY_FILE = Path.home() / ".config" / "taguri" / "gemini_api_key.txt"
_BUDGET_FILE = Path.home() / ".config" / "taguri" / "gemini_budget.json"
MAX_CALLS_PER_MONTH = int(os.environ.get("GEMINI_MAX_CALLS_PER_MONTH", "300"))


class LLMError(Exception):
    """呼び出しそのものが失敗した（鍵が無い・ネットワーク・不正な応答）。"""


class BudgetExceeded(LLMError):
    """今月の呼び出し上限（`MAX_CALLS_PER_MONTH`）を超えた。実際には呼ばずに止める。"""


class SafetyBlocked(Exception):
    """安全フィルタで止められた。**「0 件見つかった」と混ぜてはいけない。**"""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"安全フィルタで止められた（{reason}）")


def _month_key() -> str:
    return time.strftime("%Y-%m", time.gmtime())


def _check_and_count_budget() -> None:
    """呼ぶ前に確認し、成功が見込める場合だけカウントを進める。

    **厳密な原子性は求めない。** ここは「不特定多数が触れる公開デモで、
    青天井の課金を防ぐ」という目的の安全装置であり、複数プロセスが同時に
    ぎりぎりのタイミングで読み書きして数回超過する可能性はゼロではないが、
    実害は小さい（上限自体に余裕を持たせて運用する前提）。ロックファイルの
    ような複雑さを持ち込むより、単純で読める実装を優先した。
    """
    _BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)
    month = _month_key()
    data = {}
    if _BUDGET_FILE.exists():
        try:
            data = json.loads(_BUDGET_FILE.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            data = {}
    count = int(data.get(month, 0))
    if count >= MAX_CALLS_PER_MONTH:
        raise BudgetExceeded(
            f"今月のLLM呼び出し上限（{MAX_CALLS_PER_MONTH}回）に達した。"
            f"GEMINI_MAX_CALLS_PER_MONTHで調整できる。")
    data = {month: count + 1}   # 過去の月は残さない（肥大化しない）
    _BUDGET_FILE.write_text(json.dumps(data), encoding="utf-8")


def _api_key() -> str:
    v = os.environ.get("GEMINI_API_KEY")
    if v and v.strip():
        return v.strip()
    if _KEY_FILE.exists():
        v = _KEY_FILE.read_text(encoding="utf-8").strip()
        if v:
            return v
    raise LLMError(
        "GEMINI_API_KEY が無い。環境変数か "
        f"{_KEY_FILE} にキーを置く（`llm-api` スキルの守り 1）")


def ask(prompt: str, *, schema: dict | None = None, model: str = MODEL,
       timeout: int = 120, max_retries: int = 4) -> tuple[object, dict]:
    """プロンプトを投げ、JSON を返す。**呼び出し側は全員 JSON を欲しがる**ので、
    ここでは常に `responseMimeType: application/json` を付ける（自由文モードは無い）。

    `schema` を渡すと、さらに Gemini の `responseSchema` で形そのものを強制する
    （型は "OBJECT"／"ARRAY"／"STRING" など大文字。Gemini の REST API が要求する形）。
    **`schema` を渡さなくても、JSON であることまでは保証される** ── キーが動的で
    決め打ちできない出力（例: 年ごとの読みを年をキーにした辞書で返す）は、
    スキーマを付けずに使う。

    返り値は `(パースした値, メタ情報)`。メタ情報の `model_version` は、呼び出し側が
    抽出結果の行に記録するためのものである（`llm-api` スキルの再現性の守り）。

    **失敗は例外で知らせる。** 呼び出し側が「0 件見つかった」で握りつぶさないように、
    ネットワーク・鍵・不正な出力は `LLMError`、安全フィルタは `SafetyBlocked` を
    投げる ── どちらも空のリストや辞書を返さない。
    """
    key = _api_key()
    _check_and_count_budget()
    url = f"{API_BASE}/{model}:generateContent"
    gen_config: dict = {"temperature": 0, "responseMimeType": "application/json"}
    if schema is not None:
        gen_config["responseSchema"] = schema
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": gen_config,
    }).encode("utf-8")

    delay = 2.0
    data = None
    for attempt in range(max_retries):
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "x-goog-api-key": key,
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:500]
            if e.code == 429 and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise LLMError(f"Gemini API が {e.code} を返した: {detail}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise LLMError(f"Gemini API に届かなかった: {e}") from e
    if data is None:
        raise LLMError(f"429 が続いた（{max_retries} 回試した）")

    meta = {"model_version": data.get("modelVersion", model),
           "usage": data.get("usageMetadata") or {}}
    feedback = data.get("promptFeedback") or {}
    if feedback.get("blockReason"):
        raise SafetyBlocked(str(feedback["blockReason"]))
    cands = data.get("candidates") or []
    if not cands:
        raise LLMError("Gemini API が候補を 1 つも返さなかった")
    cand = cands[0]
    finish = cand.get("finishReason", "")
    if finish == "SAFETY":
        raise SafetyBlocked(finish)
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise LLMError(f"Gemini API が空の応答を返した（finishReason={finish}）")
    try:
        return json.loads(text), meta
    except json.JSONDecodeError as e:
        raise LLMError(f"Gemini API の出力が JSON として読めなかった: {text[:300]}") from e
