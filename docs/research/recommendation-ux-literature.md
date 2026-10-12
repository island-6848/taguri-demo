# 推薦UXの文献調査と、たぐりへの適用

調査日：2026-10-11。目的は「推薦から観に行きたい公演を選び、誤った好みの推測を直せる」体験の設計。
[詳細仕様](../recommendation-ux-design.md)の参照IDに対応する。全文の転載はせず、閲覧した範囲と設計への含意を記録する。

論文4件の本文の関連箇所、論文1件の著者所属機関による要旨、公式設計指針・標準を読んだ。
全ページを精読した、あるいは演劇推薦に対する実証結果を得たという意味ではない。
以下の「適用」は、研究結果からの設計上の判断であり、たぐりでの効果は別途検証する。

## R1：推薦精度と推薦体験を分ける

Knijnenburg, Willemsen, Gantner, Soncu & Newell (2012), *Explaining the user experience of recommender systems*.
User Modeling and User-Adapted Interaction 22, 441–504。
[DOI](https://doi.org/10.1007/s11257-011-9118-4)／[大学公開の本文PDF](https://pure.tue.nl/ws/portalfiles/portal/3484177/724656348730405.pdf)。

- 閲覧範囲：要旨、§2–3の評価枠組み、§4.7–4.8の実験・結果、§5の関連する考察。
- 方法：複数の実サービスの調査と統制実験を通して、システムの特性、利用者の知覚、体験、行動、利用者・状況の関係を分析。
- 読み取れること：予測精度だけでは選びやすさや満足を説明できない。候補数・多様性・知覚された品質も関係する。
- 注意：§4.7の5件／20件等の比較で、全体の選択満足度に有意差がなかった。「5件が最適」の根拠にはならない。閲覧時間の短縮だけでも成功とはいえない。
- 適用：観劇後の好みとの一致、選択完了、理由の理解を別々に測る。UIだけを比較するときは候補と順位を揃える。

## R2：推測の訂正と変化への配慮

Amershi et al. (2019), *Guidelines for Human-AI Interaction*. CHI。
[DOI](https://doi.org/10.1145/3290605.3300233)／[Microsoft Research公開の本文PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/2019/01/Guidelines-for-Human-AI-Interaction-camera-ready.pdf)。

- 閲覧範囲：要旨・導入、Table 1、検証の概要、訂正・不確実性に関する付録の例。
- 方法：18の指針を反復的に整理・評価。49名のデザイン実務者による20製品への適用を含む。
- 読み取れること：できることと限界を伝える、誤りを訂正できる、操作の影響を説明する、学習による変化を慎重に扱うことが設計指針になる。
- 注意：利用者の観劇満足が上がることを示す実験ではない。ルールによる推測にも応用できるが、効果量の保証はない。
- 適用：理由から訂正できる入口、取り消し、反映時点の表示を用意する。読んでいるカードを保存直後に自動で並べ替えない。

## R3：説明できることと、操作できること

Knijnenburg, Bostandjiev, O’Donovan & Kobsa (2012), *Inspectability and Control in Social Recommenders*. RecSys, 43–50。
[DOI](https://doi.org/10.1145/2365952.2365966)／[著者所属大学公開の本文PDF](https://ics.uci.edu/~kobsa/papers/RecSys2012.pdf)。

- 閲覧範囲：要旨、§3の実験条件・結果、§4の関連する考察。
- 方法：Facebookの音楽推薦を使う267名のオンライン実験。説明の閲覧可能性と、項目・友人への重みの操作を分けて比較。
- 読み取れること：この実験では、説明の閲覧可能性と操作可能性が理解に正の影響を持ち、知覚された制御・推薦品質・満足に関係した。
- 注意：知覚された品質は、未知の公演を実際に観た満足度とは異なる。友人グラフや重みスライダーを、そのままたぐりに導入する根拠でもない。
- 適用：自分の感想と公演の特徴との対応を見せ、誤った一般化をその場で解除できる設計を試す。グラフや数値調整を通常操作の前提にしない。

## R4：候補が多いほど悪い、とは決めない

Scheibehenne, Greifeneder & Todd (2010), *Can There Ever Be Too Many Options? A Meta-Analytic Review of Choice Overload*.
Journal of Consumer Research 37(3), 409–425。
[DOI](https://doi.org/10.1086/651235)／[著者公開の本文PDF](https://scheibehenne.de/ScheibehenneGreifenederTodd2010.pdf)。

- 閲覧範囲：要旨、分析結果、考察・限界。
- 方法：公刊・未公刊50実験、63条件、計5,036名のメタ分析。
- 読み取れること：平均効果はほぼゼロで、研究間のばらつきが大きい。候補数だけから選択過多が起きるとはいえない。
- 注意：「選択過多は存在しない」という結論にもできない。本人の既存の好みや選択状況などが異なる。
- 適用：上位15件の上限を維持し、まず各カードの比較しやすさを改善する。5件ずつ表示する案は、必要が確認された場合の独立した実験にする。

## R5：評価項目の参考。要旨のみ確認

Pu, Chen & Hu (2011), *A user-centric evaluation framework for recommender systems*. RecSys, 157–164。
[DOI](https://doi.org/10.1145/2043932.2043962)／[著者所属機関の書誌・要旨](https://scholars.hkbu.edu.hk/en/publications/a-user-centric-evaluation-framework-for-recommender-systems-8/)。

- 閲覧範囲：所属機関が掲載した要旨。本文PDFは取得できず、項目全文・分析手順は未確認。
- 読み取れること：ResQueは、推薦の品質、使いやすさ、有用性、相互作用、満足、利用意向などを扱う評価枠組み。要旨では32質問・15構成概念とされる。
- 適用：たぐりでは選びやすさ、理由の理解、訂正できる感覚、未知の候補の価値を分けて質問する。
- 注意：今回作る日本語の短い質問票を「検証済みのResQue」と呼ばない。尺度を正式に使う場合は本文・翻訳・妥当性を追加確認する。

## G1：必要な情報と詳細を分ける

Nielsen Norman Group, [Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/)。
本文の基本原則と例を確認。主な操作を先に示し、頻度の低い詳細を要求時に開く設計指針。
公演名・日時・場所まで隠す理由にはならない。論文による定量的な効果の保証ではない。
たぐりでは詳しい推薦理由・好み訂正・重み設定に適用する。

## G2：状態、取り消し、見つけやすさ

Nielsen Norman Group, [10 Usability Heuristics for User Interface Design](https://www.nngroup.com/articles/ten-usability-heuristics/)。
状態の可視性、利用者の制御、記憶への依存を減らすこと、エラーへの対処を設計レビューの観点として使う。
効果を定量的に証明する尺度ではない。たぐりの保存・通信エラー・解除・ナビゲーションを点検する。

## A1：操作可能性の基準

W3C, [WCAG 2.2](https://www.w3.org/TR/WCAG22/)。関連達成基準と、
[2.5.8 Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)、
[4.1.3 Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html)の解説を確認。

AAを設計・検証の目標とする。通常の文字は4.5:1、必要な非テキストの識別部分は3:1など、対象に応じて基準が異なる。
2.5.8の最小ターゲットは24×24 CSS pxで例外がある。たぐりの主要操作は独自の設計値として44px以上にする。
44pxをAAの必須サイズとは扱わない。保存状態は適切なライブ領域で伝え、頻繁な読み上げを避ける。
数値やチェックリストの一部を満たしただけで、サイト全体の適合を宣言しない。

## 今回の調査で決められないこと

- 演劇推薦での最適な候補数、探索比率、利用者ごとの最適な説明量。
- 感想からの特徴抽出が、実際の文章でどれだけ正確か。
- 訂正機能が推薦の順位・観劇後の満足を改善するか。
- 公開デモの実画面での操作性。今回は公開コードを確認したが、利用者観察・実機テストは未実施。

これらを論文の権威で埋めず、[詳細仕様の検証計画](../recommendation-ux-design.md#10-検証計画)で確認する。
