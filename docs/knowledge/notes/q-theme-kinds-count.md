---
id: q-theme-kinds-count
type: question
status: open
date: 2026-10-18
title: 演目を記述する言葉の種類は何種類が適切か（読書相談の appeal・NoveList・分類理論の裏付け）
sources:
  - https://www.alastore.ala.org/sites/default/files/book_samples/9780838917817_sample_0.pdf
  - https://journals.ala.org/index.php/rusq/article/view/2892/2959
  - https://about.ebsco.com/blogs/novelist/NoveList-story-elements
  - https://libraries.ne.gov/cpls/files/2023/10/NoveList-Story-Elements.pdf
  - https://files.grouplens.org/datasets/tag-genome/
  - https://e.humanities.uva.nl/publications/2015/kool_what15.pdf
  - https://flamenco.ischool.berkeley.edu/papers/hcir08.pdf
  - https://pubmed.ncbi.nlm.nih.gov/11515286/
links:
  - affects: dec-theme-kinds-1018
---
起案者の指示（2026-10-18）「別に 8 個じゃなくてもよい。何個が適切か論文など裏付けを調べて」。

**確かめ方の限界**: このセッションでは出典のページを開けなかった（WebFetch が名前解決できない）。以下はすべて検索結果の抜粋で、本文は未確認。企画書に載せる前に原典で確かめる。

分かったこと（未確認）:
- 読書相談（readers' advisory）の appeal 要素は、Saricks の Genre Fiction の版で 6 つ（Pacing・Characterization・Storyline・Tone/Mood・Frame/Setting・Style/Language）。1997 年版は 5 つ。Nancy Pearl の入口は 4 つ（Story・Character・Setting・Language）
- NoveList の story elements は 6 種類（appeals・genres・themes・subjects・identities・time and place）で、題材（subjects）とテーマ（themes）を分けている。感情の面は Tone（Bittersweet・Heartwarming など）に入る
- 好みを表す言葉の推薦は、作品をまたいで共通に使える語彙の上に成り立つ（MovieLens の Tag Genome・Netflix の altgenre）。作品固有の言葉は照合に効きにくい
- 分類理論の PMEST は基本範疇 5 つ。多基準推薦で基準を増やすと精度が上がった報告はあるが、「種類が多いほどよい」一般則は見つからない
- 画面に一度に見せるファセットは 4〜5 個の例（Hearst が紹介した eBay Express）。短期記憶は約 4 チャンク（Cowan 2001）。これは表示の話で、照合の種類数とは別
- 演劇に固有の、好みを記述する分類は見つからなかった（ECLAP・Linked Stage Graph などは上演を出来事として記録するためのモデル）

調査役の推した形（照合 6 種類＋属性 2）: ジャンル／題材／テーマ（善と悪・親子などの関係と対立の軸）／舞台設定／味わい（トーン。切ない などの感情もここ）／語り口・上演様式（群像劇・会話劇・二人芝居・テンポ。新設）。属性として原作・作者（完全一致）とモチーフ（理由の表示だけ）。

いまの 8 種類との違い: 「関係・感情」を関係（→テーマ）と感情（→味わい）に分ける。「構造」を対立の軸（→テーマ）と語り口（→上演様式）に分ける。性質の違う言葉を同じ種類に入れると、種類ごとの重さが意味を持たなくなるため。

次に決めること: 6＋2 に組み替えるか。大量の読み取りの前に決める（組み替えは指示文と THEME_KIND_W を直すだけで、読み直しの費用は変わらない）。
