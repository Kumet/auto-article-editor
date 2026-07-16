# Render Freeデプロイ手順

このドキュメントでは、`auto-article-editor` をRenderのFree Web Serviceへ
デプロイする方法を説明します。生成した記事はWordPressへ自動送信せず、
ブラウザのクリップボードへコピーして使用します。

## Freeプラン向けの構成

リポジトリ直下の `render.yaml` は次の内容で設定済みです。

- Web Service
- Freeインスタンス
- Python 3.12
- Singaporeリージョン
- `/health` によるHTTPヘルスチェック
- HTTP Basic認証
- 一時設定ファイル: `/tmp/auto-article-editor/settings.json`

Render Freeのファイルシステムは一時的です。スピンダウン、再起動、
再デプロイ後は、設定画面から保存した記事の型が消える場合があります。
永続化したい記事の型は `DEFAULT_ARTICLE_TEMPLATE` へ設定してください。

Render公式資料:

- [Deploy for Free](https://render.com/docs/free)
- [FastAPIのデプロイ](https://render.com/docs/deploy-fastapi)
- [Blueprint YAML Reference](https://render.com/docs/blueprint-spec)
- [Environment Variables and Secrets](https://render.com/docs/configure-environment-variables)
- [Health Checks](https://render.com/docs/health-checks)

## デプロイ前に用意するもの

1. OpenAI APIキー
2. このアプリへログインするユーザー名
3. このアプリへログインする強いパスワード

WordPress URL、WordPressユーザー名、アプリケーションパスワードは不要です。

## 方法1: Blueprintから作成する

### 1. GitHubリポジトリを接続する

1. [Render Dashboard](https://dashboard.render.com/)へログインします。
2. `New` → `Blueprint` を選択します。
3. GitHubを接続し、`Kumet/auto-article-editor` を選択します。
4. リポジトリ直下の `render.yaml` が認識されていることを確認します。

### 2. シークレットを入力する

Blueprint作成時に次の環境変数を入力します。

| キー | 設定内容 |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI APIキー |
| `APP_USERNAME` | アプリへログインするユーザー名 |
| `APP_PASSWORD` | アプリへログインする強いパスワード |

`APP_USERNAME` と `APP_PASSWORD` は必ず設定してください。未設定の場合、第三者への
公開を防ぐためアプリはHTTP 503を返します。

次の環境変数は `render.yaml` で設定済みです。

| キー | 値 |
| --- | --- |
| `OPENAI_MODEL` | `gpt-5` |
| `APP_SETTINGS_PATH` | `/tmp/auto-article-editor/settings.json` |
| `APP_SETTINGS_EPHEMERAL` | `true` |

### 3. Blueprintの内容を確認する

| 項目 | 値 |
| --- | --- |
| Runtime | Python |
| Region | Singapore |
| Plan | Free |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |
| Persistent Disk | なし |

内容に問題がなければBlueprintを適用します。

## 方法2: Web Serviceを手動作成する

### 基本設定

| 項目 | 値 |
| --- | --- |
| Service Type | Web Service |
| Repository | `Kumet/auto-article-editor` |
| Branch | `main` |
| Language | Python 3 |
| Region | Singapore |
| Instance Type | Free |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

永続ディスクは追加しません。

### 環境変数

Environment画面で次を登録します。

```text
OPENAI_API_KEY=<OpenAI APIキー>
OPENAI_MODEL=gpt-5

APP_USERNAME=<アプリ用ユーザー名>
APP_PASSWORD=<アプリ用パスワード>

APP_SETTINGS_PATH=/tmp/auto-article-editor/settings.json
APP_SETTINGS_EPHEMERAL=true
```

値をGitHubのファイルや `render.yaml` へ直接書かないでください。

## 記事の型を永続的に変更する

環境変数 `DEFAULT_ARTICLE_TEMPLATE` は任意です。未設定の場合は、アプリ内蔵の
SEO・AIO向けテンプレートを使用します。

Render DashboardのEnvironmentへ複数行のテンプレートを登録できます。

```text
DEFAULT_ARTICLE_TEMPLATE=読みやすい日本語の記事にリライトし、H2・H3見出しで整理してください。
```

設定画面から変更した型は稼働中には有効ですが、スピンダウンや再起動後には
`DEFAULT_ARTICLE_TEMPLATE` の値へ戻ります。

## デプロイ後の確認

次の順番で確認します。

1. `https://<サービス名>.onrender.com/health` がHTTP 200を返す
2. トップページがBasic認証なしではHTTP 401を返す
3. `APP_USERNAME` と `APP_PASSWORD` でログインできる
4. 設定画面にデフォルトの記事の型が表示される
5. 記事URLからプレビューを作成できる
6. 「タイトルをコピー」でタイトルをコピーできる
7. 「記事本文をコピー」で本文をコピーできる
8. コピー先のブログやCMSへ書式付きで貼り付けられる

クリップボードAPIはHTTPSまたはlocalhostで利用できます。Renderの公開URLはHTTPSのため、
通常は追加設定なしで動作します。

## 自動デプロイ

GitHub連携で作成したサービスは、通常 `main` へのpushを検知して自動デプロイします。
Render DashboardのSettingsでAuto-Deployが有効か確認してください。

自動デプロイすると一時設定ファイルは消えますが、環境変数へ登録した
OpenAI APIキー、Basic認証、デフォルトの記事の型は保持されます。

## トラブルシューティング

### 設定が消えた

Freeプランでは正常な動作です。永続化したい記事の型を
`DEFAULT_ARTICLE_TEMPLATE` としてEnvironmentへ登録してください。

### ヘルスチェックが失敗する

- Health Check Pathが `/health` か確認する
- `APP_USERNAME` と `APP_PASSWORD` の両方が設定されているか確認する
- Logsでアプリ起動時の例外を確認する

### HTTP 503が返る

`APP_USERNAME` または `APP_PASSWORD` が未設定です。両方を設定し、
`Save and deploy` を実行してください。

### HTTP 401が返る

Basic認証が有効です。ブラウザへ `APP_USERNAME` と `APP_PASSWORD` を入力してください。

### `No open ports detected`

Start Commandが次の内容か確認します。

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### コピーできない

- ブラウザのクリップボード権限を許可する
- RenderのHTTPS URLでアプリを開く
- シークレットモードやブラウザ拡張機能による制限を確認する
- 別の対応ブラウザで試す

リッチテキストコピーに対応していないブラウザでは、HTML文字列のコピーへ
自動的に切り替わります。

### OpenAIで記事を生成できない

- `OPENAI_API_KEY` が設定されているか確認する
- APIキーの利用上限と請求設定を確認する
- `OPENAI_MODEL` が利用可能か確認する

## Freeプランの注意事項

- 15分間アクセスがないとスピンダウンする
- 次のアクセス時は起動に時間がかかる
- ローカルファイルはスピンダウン、再起動、再デプロイで消える
- 永続ディスクは使用できない
- 月間のFree instance hours、帯域、ビルド時間に上限がある

## セキュリティ上の注意

- APIキーやパスワードをGitHubへコミットしない
- `APP_PASSWORD` は他サービスと使い回さない
- Basic認証を無効にしない
- 不要になったOpenAI APIキーは失効させる
