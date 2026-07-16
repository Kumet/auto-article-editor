# 記事編集アプリ 詳細設計書

## 目的

記事URLを入力し、AIでHTML記事へリライトする。生成内容をプレビューしてから、
タイトルと本文をクリップボードへコピーし、WordPressなどのCMSへ手動で貼り付ける。

## 開発方針

- FastAPI + HTMX
- 個人利用専用
- DBなし
- Dockerなし
- 非同期ジョブなし
- 設定はローカルJSONへ保存
- WordPress REST APIへの自動保存は行わない

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
        app.js
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

返却はWordPressなどの本文欄へ貼り付けられるHTML断片。

### settings.py

```python
load_settings() -> dict
save_settings(default_template: str) -> dict
```

保存項目:

- デフォルトの記事の型

### wordpress.py

```python
sanitize_article_html(content: str) -> str
```

生成されたHTMLはプレビューとコピーの前にサニタイズする。

## API

### GET /

記事編集画面を表示する。

入力:

- 元記事のURL
- 記事の型

記事の型には設定画面で保存したデフォルト値を表示する。

### POST /generate

処理:

1. 記事取得
2. 本文抽出
3. HTMLへAIリライト
4. HTMLをサニタイズ
5. プレビューを返却

### GET /settings

設定画面を表示する。

### POST /settings

デフォルトの記事の型を `data/settings.json` に保存する。

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
- 記事プレビュー
- 編集可能な記事タイトル
- タイトルをコピーボタン
- 記事本文をコピーボタン
- コピー結果通知

### コピー時のUX

- タイトルはプレーンテキストでコピーする
- 本文は `text/html` と `text/plain` の両形式をクリップボードへ登録する
- リッチコピー非対応時はHTML文字列のコピーへフォールバックする
- 成功時はボタンを一時的に「コピーしました ✓」へ変更する
- 成功・失敗を画面右下の通知と `aria-live` で伝える
- Clipboard APIが使えない場合は従来のコピー処理へフォールバックする

### 設定

- デフォルトの記事の型
- 設定保存ボタン

### 使い方

記事の型の設定、プレビュー作成、クリップボードコピーの手順を表示する。

## OpenAI

入力:

- 元記事のタイトル
- 元記事の本文
- 記事の型

出力:

- CMS本文向けHTML断片
- `html`、`head`、`body`、`h1` は含めない
- Markdownは出力しない

## 環境変数

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5

APP_USERNAME=
APP_PASSWORD=
APP_SETTINGS_PATH=
APP_SETTINGS_EPHEMERAL=
DEFAULT_ARTICLE_TEMPLATE=
```

Render Freeでは画面変更を
`APP_SETTINGS_PATH=/tmp/auto-article-editor/settings.json` へ一時保存する。
記事の型は `DEFAULT_ARTICLE_TEMPLATE` で永続的な初期値を指定できる。
`APP_USERNAME` と `APP_PASSWORD` は公開環境のBasic認証に使用する。

## 実装しないもの

- WordPress REST APIへの下書き保存
- WordPress接続テスト
- DB
- Docker
- Redis
- Celery
- 認証画面
- リッチエディタ
- オートセーブ
- 履歴
- 一括処理
- 画像生成
