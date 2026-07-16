# 記事編集アプリ 詳細設計書（Codex最適化版）

## 目的

記事URLを入力し、AIでWordPress用の記事へリライトし、プレビューを確認して
設定済みのWordPressへ下書き保存する。

## 開発方針

- FastAPI + HTMX
- 個人利用専用
- JavaScriptを書かない
- DBなし
- Dockerなし
- 非同期処理なし
- 設定はローカルJSONへ保存

## ディレクトリ構成

```text
app/
    main.py
    extractor.py
    llm.py
    settings.py
    wordpress.py

    templates/
        base.html
        index.html
        preview.html
        settings.html
        guide.html

    static/
        styles.css

data/
    settings.json

.env
requirements.txt
```

`data/settings.json` はアプリの初回設定保存時に作成し、Git管理対象外とする。

## 関数一覧

### extractor.py

```python
extract_article(url: str) -> dict
```

返却:

```python
{
    "title": str,
    "content": str,
}
```

### llm.py

```python
rewrite_article(article: str, template: str) -> str
```

返却はWordPress本文欄へ登録できるHTML断片。

### settings.py

```python
load_settings() -> dict
save_settings(default_template: str, wp_url: str) -> dict
```

保存項目:

- デフォルトの記事の型
- 保存先のWordPress URL

### wordpress.py

```python
sanitize_article_html(content: str) -> str
save_draft(title: str, content: str, wp_url: str) -> bool
```

生成されたHTMLはプレビュー前とWordPress送信前にサニタイズする。

## API

### GET /

記事編集画面。

入力:

- 元記事のURL
- 記事の型

記事の型には設定画面で保存したデフォルト値を表示する。

### POST /generate

処理:

1. 記事取得
2. 本文抽出
3. WordPress用HTMLへAIリライト
4. HTMLをサニタイズ
5. プレビューを返却

### POST /save

入力:

- title
- content

設定済みのWordPress URLへ `draft` として保存する。

### GET /settings

設定画面。

### POST /settings

デフォルトの記事の型とWordPress URLを `data/settings.json` に保存する。

### GET /guide

アプリの使い方を表示する。

### GET /health

RenderのHTTPヘルスチェック用。正常時にHTTP 200と `{"status": "ok"}` を返す。

## UI

共通ヘッダーに3つのタブを表示する。

- 記事編集
- 設定
- 使い方

### 記事編集

- 元記事URL
- 記事の型
- プレビュー作成ボタン
- WordPress記事プレビュー
- 記事タイトル
- WordPressへの下書き保存ボタン

### 設定

- デフォルトの記事の型
- 保存先のWordPress URL
- 設定保存ボタン

WordPressのユーザー名とアプリケーションパスワードは画面には保存しない。

### 使い方

初期設定、プレビュー作成、下書き保存の手順を表示する。

## OpenAI

入力:

- 元記事のタイトル
- 元記事の本文
- 記事の型

出力:

- WordPress本文向けHTML断片
- `html`、`head`、`body`、`h1` は含めない
- Markdownは出力しない

## WordPress

REST API:

```text
POST /wp-json/wp/v2/posts
```

送信:

- `title`
- `content`
- `status=draft`

認証はApplication Passwordを使用する。

## 環境変数

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5

WP_USERNAME=
WP_APP_PASSWORD=

APP_USERNAME=
APP_PASSWORD=
APP_SETTINGS_PATH=
```

保存先URLは環境変数ではなく設定画面から登録する。
Renderでは `APP_SETTINGS_PATH=/var/data/settings.json` とし、永続ディスクへ保存する。
`APP_USERNAME` と `APP_PASSWORD` は公開環境のBasic認証に使用する。

## 実装しないもの

- DB
- Docker
- Redis
- Celery
- 認証画面
- リッチエディタ
- オートセーブ
- 履歴
- 一括処理
- SEO分析
- 画像生成
- カテゴリ・タグ管理
