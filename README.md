# auto-article-editor

記事URLから本文を抽出し、OpenAI APIで指定フォーマットのMarkdownへリライトして、
内容を確認・編集したうえでWordPressへ下書き保存する個人向けWebアプリです。

## 主な機能

- 記事URLからタイトルと本文を抽出
- 自由入力の出力形式に従ってAIリライト
- HTMLプレビューとMarkdown編集画面を横並び表示
- WordPress REST APIへ下書きとして保存
- FastAPI + HTMXによるJavaScriptコード不要の構成

## セットアップ

Python 3.10以上を使用してください。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` に接続情報を設定します。

```dotenv
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5

WP_URL=https://example.com
WP_USERNAME=your-wordpress-username
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

WordPressのアプリケーションパスワードは、管理画面のユーザープロフィールから発行できます。

## 起動

```bash
uvicorn app.main:app --reload
```

ブラウザで http://127.0.0.1:8000 を開きます。

## 使い方

1. リライト元の記事URLを入力する
2. 見出し構成や文体などの出力形式を指定する
3. 「記事を生成」を押す
4. プレビューを確認し、必要に応じてタイトルとMarkdownを編集する
5. 「WordPressへ保存」を押す

WordPressには `draft` ステータスで保存され、公開はされません。

## 構成

```text
app/
├── main.py
├── extractor.py
├── llm.py
├── wordpress.py
├── templates/
│   ├── index.html
│   └── preview.html
└── static/
    └── styles.css
```

詳細設計は
[`docs/article-editor-design-codex-optimized.md`](docs/article-editor-design-codex-optimized.md)
を参照してください。
