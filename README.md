# auto-article-editor

記事URLから本文を抽出し、OpenAI APIでWordPress用のHTML記事へリライトして、
プレビュー確認後にWordPressへ下書き保存する個人向けWebアプリです。

## 主な機能

- 記事URLからタイトルと本文を抽出
- 保存した「記事の型」に従ってWordPress用HTMLを生成
- WordPressへ保存する前に記事をプレビュー
- WordPress REST APIへ下書きとして保存
- 記事編集・設定・使い方の3画面
- FastAPI + HTMXによるJavaScriptコード不要の構成

## セットアップ

Python 3.10以上を使用してください。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` にOpenAIとWordPressの認証情報を設定します。

```dotenv
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5

WP_USERNAME=your-wordpress-username
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
WP_URL=https://example.com
```

WordPressのアプリケーションパスワードは、管理画面のユーザープロフィールから発行できます。
保存先のWordPress URLは、アプリの「設定」タブで登録します。

## 起動

```bash
uvicorn app.main:app --reload
```

ブラウザで http://127.0.0.1:8000 を開きます。

## Renderへデプロイ

リポジトリ直下の `render.yaml` を使い、Render Dashboardで `New` → `Blueprint` から
このリポジトリを選択します。Free Web Service用に設定済みです。

作成時に次のシークレットを入力してください。

- `OPENAI_API_KEY`
- `WP_URL`
- `WP_USERNAME`
- `WP_APP_PASSWORD`
- `APP_USERNAME`
- `APP_PASSWORD`

Freeインスタンスでは設定画面から保存した値がスピンダウン、再起動、再デプロイで消えます。
WordPress URLは `WP_URL`、永続的な記事の型は任意の
`DEFAULT_ARTICLE_TEMPLATE` としてRenderのEnvironmentへ設定してください。
`DEFAULT_ARTICLE_TEMPLATE` を設定しない場合は、検索意図への先行回答、比較表、
注意点、FAQなどを含むアプリ内蔵のSEO・AIO向けテンプレートが使用されます。

詳しい手順とトラブルシューティングは
[`docs/render-deployment.md`](docs/render-deployment.md) を参照してください。

## 使い方

1. 「設定」タブでデフォルトの記事の型とWordPress URLを保存する
2. 「記事編集」タブで元記事のURLを入力する
3. 必要に応じて今回の記事の型を調整する
4. 「プレビューを作成」を押す
5. WordPress記事のプレビューとタイトルを確認する
6. 「WordPressへ下書き保存」を押す

WordPressには `draft` ステータスで保存され、公開はされません。

## 設定の保存場所

ローカルでは、画面で登録した記事の型とWordPress URLを `data/settings.json` に保存します。
Render Freeでは一時ファイルへ保存され、再起動後は `WP_URL` と
`DEFAULT_ARTICLE_TEMPLATE` の環境変数へ戻ります。

## 構成

```text
app/
├── auth.py
├── main.py
├── extractor.py
├── llm.py
├── settings.py
├── wordpress.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── settings.html
│   ├── guide.html
│   └── preview.html
└── static/
    └── styles.css

render.yaml
.python-version
```

詳細設計は
[`docs/article-editor-design-codex-optimized.md`](docs/article-editor-design-codex-optimized.md)
を参照してください。
