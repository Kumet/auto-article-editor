# 記事編集アプリ 詳細設計書（Codex最適化版）

## 目的

記事URLを入力し、AIで指定フォーマットへリライトし、内容を確認してWordPressへ下書き保存する。

## 開発方針

-   FastAPI + HTMX
-   実装速度最優先
-   個人利用専用
-   YAGNI徹底
-   JavaScriptを書かない（HTMXのみ）
-   DBなし
-   Dockerなし
-   非同期処理なし
-   テストコードなし

------------------------------------------------------------------------

# ディレクトリ構成

``` text
app/
    main.py
    extractor.py
    llm.py
    wordpress.py

    templates/
        index.html
        preview.html

    static/

.env
requirements.txt
```

------------------------------------------------------------------------

# 関数一覧

## extractor.py

``` python
extract_article(url: str) -> dict
```

返却

``` python
{
    "title": str,
    "content": str
}
```

------------------------------------------------------------------------

## llm.py

``` python
rewrite_article(
    article: str,
    template: str
) -> str
```

返却

Markdown全文

------------------------------------------------------------------------

## wordpress.py

``` python
save_draft(
    title: str,
    markdown: str
) -> bool
```

------------------------------------------------------------------------

# API

## GET /

トップ画面

------------------------------------------------------------------------

## POST /generate

入力

-   url
-   template

処理

1.  記事取得
2.  本文抽出
3.  AIリライト
4.  preview.html返却

------------------------------------------------------------------------

## POST /save

入力

-   title
-   markdown

処理

WordPressへdraft保存

------------------------------------------------------------------------

# HTMX

index.html

``` html
<form
 hx-post="/generate"
 hx-target="#result"
 hx-swap="innerHTML">
```

返却

preview.html

JavaScriptは書かない。

------------------------------------------------------------------------

# UI

初期画面

-   URL入力
-   出力形式
-   生成ボタン

生成後

左

-   HTMLプレビュー

右

-   Markdown textarea

下部

-   WordPressへ保存

------------------------------------------------------------------------

# OpenAI

入力

-   タイトル
-   本文
-   出力形式

出力

Markdown

------------------------------------------------------------------------

# WordPress

REST API

POST

/wp-json/wp/v2/posts

送信

-   title
-   content
-   status=draft

認証

Application Password

------------------------------------------------------------------------

# 環境変数

``` text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5

WP_URL=
WP_USERNAME=
WP_APP_PASSWORD=
```

------------------------------------------------------------------------

# requirements.txt

``` text
fastapi
uvicorn
jinja2
python-dotenv
requests
beautifulsoup4
readability-lxml
markdown
openai
```

------------------------------------------------------------------------

# 実装順

1.  FastAPI起動
2.  index.html
3.  HTMX導入
4.  extract_article()
5.  rewrite_article()
6.  preview表示
7.  textarea編集
8.  save_draft()

------------------------------------------------------------------------

# 実装しない

-   DB
-   Docker
-   Redis
-   Celery
-   クラス設計
-   Pydantic DTO
-   認証画面
-   管理画面
-   リッチエディタ
-   オートセーブ
-   履歴
-   一括処理
-   SEO分析
-   画像生成
-   カテゴリ取得
-   タグ取得

------------------------------------------------------------------------

# 開発ルール

-   関数ベースで実装する
-   クラスは作らない
-   型ヒントを付ける
-   共通化は必要になってから
-   同期処理で実装
-   まずMVPを完成させる
