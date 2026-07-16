# Render Freeデプロイ手順

このドキュメントでは、`auto-article-editor` をRenderのFree Web Serviceへ
デプロイする方法を説明します。実際のデプロイ操作はRender Dashboardから行ってください。

## Freeプラン向けの構成

リポジトリ直下の `render.yaml` はFreeプラン用に設定済みです。

- Web Service
- Freeインスタンス
- Python 3.12
- Singaporeリージョン
- `/health` によるHTTPヘルスチェック
- HTTP Basic認証
- 一時設定ファイル: `/tmp/auto-article-editor/settings.json`

Render Freeのファイルシステムは一時的です。15分間アクセスがない場合のスピンダウン、
再起動、再デプロイが発生すると、画面から保存した設定ファイルは消えます。また、
Free Web Serviceでは永続ディスクを利用できません。

この制約に対応するため、アプリは次の順番で設定を読み込みます。

1. 稼働中に設定画面から保存した一時設定
2. Renderの環境変数
3. アプリ内蔵のデフォルト値

再起動後も保持したい値は、必ずRenderの環境変数へ登録してください。

Render公式資料:

- [Deploy for Free](https://render.com/docs/free)
- [FastAPIのデプロイ](https://render.com/docs/deploy-fastapi)
- [Blueprint YAML Reference](https://render.com/docs/blueprint-spec)
- [Environment Variables and Secrets](https://render.com/docs/configure-environment-variables)
- [Health Checks](https://render.com/docs/health-checks)

## デプロイ前の準備

次の情報を用意します。

1. OpenAI APIキー
2. 保存先WordPressのトップURL
3. WordPressのユーザー名
4. WordPressのアプリケーションパスワード
5. このアプリへログインするユーザー名と強いパスワード

WordPress URLは次の形式です。

```text
https://example.com
```

末尾に `/wp-json` や `/wp-json/wp/v2/posts` は付けません。

## 方法1: Blueprintから新規作成する

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
| `WP_USERNAME` | WordPressのユーザー名 |
| `WP_APP_PASSWORD` | WordPressのアプリケーションパスワード |
| `WP_URL` | WordPressのトップURL |
| `APP_USERNAME` | このアプリへログインするユーザー名 |
| `APP_PASSWORD` | このアプリへログインする強いパスワード |

`APP_USERNAME` と `APP_PASSWORD` は必ず設定してください。未設定の場合、アプリは
第三者へ公開されることを防ぐためHTTP 503を返します。

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

## 既存のRenderサービスを更新する場合

以前の `render.yaml` はStarterインスタンスと永続ディスクを指定していました。
Freeサービスでは、最新の `main` をデプロイして次を確認してください。

1. Instance Typeが `Free` になっている
2. Persistent Diskが設定されていない
3. `APP_SETTINGS_PATH=/tmp/auto-article-editor/settings.json`
4. `APP_SETTINGS_EPHEMERAL=true`
5. `WP_URL` がEnvironmentへ登録されている

Blueprintの `sync: false` 環境変数は、既存Blueprintの更新時には新しい値の入力を
求められません。今回追加された `WP_URL` が存在しない場合は、Render Dashboardで
サービスを開き、`Environment` から手動で追加してください。

## 方法2: Web Serviceを手動作成する

Blueprintを使わない場合は次の値を入力します。

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

WP_URL=https://example.com
WP_USERNAME=<WordPressユーザー名>
WP_APP_PASSWORD=<WordPressアプリケーションパスワード>

APP_USERNAME=<アプリ用ユーザー名>
APP_PASSWORD=<アプリ用パスワード>

APP_SETTINGS_PATH=/tmp/auto-article-editor/settings.json
APP_SETTINGS_EPHEMERAL=true
```

値をGitHubのファイルや `render.yaml` へ直接書かないでください。

## デフォルトの記事の型を永続的に変更する

環境変数 `DEFAULT_ARTICLE_TEMPLATE` は任意です。未設定の場合は、検索意図への
先行回答、比較、注意点、FAQ、WordPress向けHTML出力を指定したアプリ内蔵の
SEO・AIO向けテンプレートを使用します。

Render DashboardのEnvironmentへ、次のように追加できます。

```text
DEFAULT_ARTICLE_TEMPLATE=読みやすい日本語の記事にリライトし、H2・H3見出しで整理してください。
```

複数行の値も設定できます。

設定画面から変更した型は稼働中には有効ですが、スピンダウンや再起動後には
`DEFAULT_ARTICLE_TEMPLATE` の値へ戻ります。

## 設定画面の動作

Freeプランでは設定画面に注意メッセージが表示されます。

- 設定画面の保存内容は現在のインスタンスが動いている間だけ有効
- スピンダウン、再起動、再デプロイ後は環境変数へ戻る
- WordPress URLを永続化するには `WP_URL` を変更する
- 記事の型を永続化するには `DEFAULT_ARTICLE_TEMPLATE` を変更する

環境変数を変更するとRenderが再デプロイするため、画面から一時保存した値は消え、
新しい環境変数の値が表示されます。

## デプロイ後の確認

次の順番で確認します。

1. `https://<サービス名>.onrender.com/health` がHTTP 200を返す
2. トップページがBasic認証なしではHTTP 401を返す
3. `APP_USERNAME` と `APP_PASSWORD` でログインできる
4. 設定画面に `WP_URL` の値が表示される
5. 記事URLからプレビューを作成できる
6. WordPressへ下書き保存できる
7. WordPress管理画面で記事が「下書き」になっている

Freeサービスは15分間アクセスがないとスピンダウンします。次のアクセス時は起動に
約1分かかる場合があります。

## 自動デプロイ

GitHub連携で作成したサービスは、通常 `main` へのpushを検知して自動デプロイできます。
Render DashboardのSettingsでAuto-Deployが有効か確認してください。

自動デプロイが実行されると一時設定ファイルは消えますが、環境変数に登録した
WordPress URL、認証情報、デフォルトの記事の型は保持されます。

## トラブルシューティング

### Blueprintで有料プランやディスクのエラーが出る

最新の `main` にある `render.yaml` を使用しているか確認します。

```yaml
plan: free
```

`disk:` セクションが残っている場合は古いファイルです。

### 設定が消えた

Freeプランでは正常な動作です。次をRenderのEnvironmentへ登録してください。

- `WP_URL`
- `DEFAULT_ARTICLE_TEMPLATE`（任意）

画面からの変更は一時設定としてのみ使用してください。

### WordPress URLが空になる

Render DashboardのEnvironmentに `WP_URL` が設定されているか確認します。
値を保存した後、サービスを再デプロイしてください。

### ヘルスチェックが失敗する

- Health Check Pathが `/health` か確認する
- `APP_USERNAME` と `APP_PASSWORD` の両方が設定されているか確認する
- Logsでアプリ起動時の例外を確認する

### HTTP 503が返る

`APP_USERNAME` または `APP_PASSWORD` が未設定です。両方を設定して再デプロイしてください。

### HTTP 401が返る

Basic認証が有効です。ブラウザへ `APP_USERNAME` と `APP_PASSWORD` を入力してください。

### `No open ports detected`

Start Commandが次の内容か確認します。

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### WordPressへの保存に失敗する

- `WP_URL` に `/wp-json` を付けていないか確認する
- `WP_USERNAME` がアプリケーションパスワードを発行したユーザーか確認する
- `WP_APP_PASSWORD` が正しいか確認する
- WordPress REST APIが外部からアクセス可能か確認する
- セキュリティプラグインがREST APIを遮断していないか確認する

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
- 外部APIへの通信量が極端に多い場合、サービスが停止される可能性がある

詳細はRender公式の
[Deploy for Free](https://render.com/docs/free) を確認してください。

## セキュリティ上の注意

- APIキーやパスワードをGitHubへコミットしない
- `APP_PASSWORD` は他サービスと使い回さない
- Basic認証を無効にしない
- 不要になったOpenAIキーとWordPressアプリケーションパスワードは失効させる
- WordPressでは必要最小限の権限を持つ専用ユーザーの利用を検討する
