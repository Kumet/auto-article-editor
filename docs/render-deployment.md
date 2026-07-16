# Renderデプロイ手順

このドキュメントでは、`auto-article-editor` をRenderのWeb Serviceとして公開する方法を説明します。
実際のデプロイ操作はRender Dashboardから行ってください。

## 推奨構成

このアプリは設定画面で次の値をローカルJSONへ保存します。

- デフォルトの記事の型
- 保存先のWordPress URL

Renderの通常のファイルシステムは再デプロイや再起動で消えるため、設定を保持するには
永続ディスクが必要です。永続ディスクは有料Web Serviceでのみ使用できます。
この手順のStarterインスタンスと永続ディスクには料金が発生します。作成を確定する前に、
Render Dashboardに表示される最新料金を確認してください。

このリポジトリの `render.yaml` は次の推奨構成です。

- Web Service
- Python 3.12
- Singaporeリージョン
- Starterインスタンス
- 1GB永続ディスク
- `/var/data/settings.json` にアプリ設定を保存
- `/health` をHTTPヘルスチェックに使用
- HTTP Basic認証でアプリ全体を保護

`requirements.txt` は検証済みの主要パッケージをバージョン固定しているため、
Renderでもローカル検証時と同じ構成を再現しやすくしています。

Render公式資料:

- [FastAPIのデプロイ](https://render.com/docs/deploy-fastapi)
- [Web Services](https://render.com/docs/web-services)
- [Blueprint YAML Reference](https://render.com/docs/blueprint-spec)
- [Persistent Disks](https://render.com/docs/disks)
- [Environment Variables and Secrets](https://render.com/docs/configure-environment-variables)
- [Health Checks](https://render.com/docs/health-checks)

## デプロイ前の準備

以下を用意します。

1. Renderアカウント
2. GitHub上のこのリポジトリへのアクセス権
3. OpenAI APIキー
4. WordPressのユーザー名
5. WordPressのアプリケーションパスワード
6. アプリへログインするための任意のユーザー名と強いパスワード

WordPressのアプリケーションパスワードは通常のログインパスワードとは別に、
WordPress管理画面のユーザープロフィールから発行します。

## 方法1: Blueprintから作成する（推奨）

リポジトリ直下の `render.yaml` を使う方法です。起動コマンド、環境変数、
ヘルスチェック、永続ディスクがまとめて設定されます。

### 1. RenderへGitHubを接続する

1. [Render Dashboard](https://dashboard.render.com/)へログインします。
2. GitHubアカウントを接続します。
3. `Kumet/auto-article-editor` リポジトリへのアクセスを許可します。

### 2. Blueprintを作成する

1. Render Dashboardで `New` を押します。
2. `Blueprint` を選択します。
3. `auto-article-editor` リポジトリを選択します。
4. Blueprintファイルとしてリポジトリ直下の `render.yaml` が認識されることを確認します。
5. サービス名が既に使われている場合は、`render.yaml` の `name` を変更してGitHubへpushしてから
   再度作成します。

### 3. シークレット環境変数を入力する

Blueprint作成時に、`sync: false` の環境変数の入力を求められます。

| キー | 設定内容 |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI APIキー |
| `WP_USERNAME` | WordPressのユーザー名 |
| `WP_APP_PASSWORD` | WordPressのアプリケーションパスワード |
| `APP_USERNAME` | このアプリへログインするユーザー名 |
| `APP_PASSWORD` | このアプリへログインする強いパスワード |

`APP_USERNAME` と `APP_PASSWORD` は必ず設定してください。RenderのWeb Serviceは
`onrender.com` の公開URLを持つため、未設定のままだと第三者がアプリを利用できます。
アプリはRender上でこの2項目が揃っていない場合、HTTP 503を返して利用を拒否します。

次の値は `render.yaml` で設定済みです。

| キー | 値 | 用途 |
| --- | --- | --- |
| `OPENAI_MODEL` | `gpt-5` | 記事生成モデル |
| `APP_SETTINGS_PATH` | `/var/data/settings.json` | 永続ディスク上の設定ファイル |

### 4. 作成内容を確認する

作成前に次を確認します。

- Runtime: `Python`
- Region: `Singapore`
- Plan: `Starter`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`
- Disk Mount Path: `/var/data`
- Disk Size: `1 GB`

内容に問題がなければBlueprintを適用します。Renderがビルドとデプロイを開始します。

### 5. デプロイ完了を確認する

1. RenderのEventsまたはLogsを開きます。
2. 依存関係のインストールが成功していることを確認します。
3. Uvicornが `0.0.0.0` とRenderの `PORT` で起動していることを確認します。
4. サービスの `https://...onrender.com` URLを開きます。
5. Basic認証ダイアログへ `APP_USERNAME` と `APP_PASSWORD` を入力します。
6. 「設定」タブで記事の型とWordPress URLを保存します。
7. ページを再読み込みし、設定が保持されることを確認します。

`https://...onrender.com/health` は認証なしで次のレスポンスを返します。

```json
{"status":"ok"}
```

## 方法2: Web Serviceを手動作成する

Blueprintを使わない場合は、Render Dashboardで次のように設定します。

### 基本設定

| 項目 | 値 |
| --- | --- |
| Service Type | Web Service |
| Repository | `Kumet/auto-article-editor` |
| Branch | `main` |
| Language | Python 3 |
| Region | Singapore |
| Instance Type | Starter以上 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

### 環境変数

Environment画面で次を登録します。

```text
OPENAI_API_KEY=<OpenAI APIキー>
OPENAI_MODEL=gpt-5
WP_USERNAME=<WordPressユーザー名>
WP_APP_PASSWORD=<WordPressアプリケーションパスワード>
APP_USERNAME=<アプリ用ユーザー名>
APP_PASSWORD=<アプリ用パスワード>
APP_SETTINGS_PATH=/var/data/settings.json
```

値をGitHubのファイルや `render.yaml` に直接書かないでください。

### 永続ディスク

AdvancedまたはDisks画面からディスクを追加します。

| 項目 | 値 |
| --- | --- |
| Name | `settings` |
| Mount Path | `/var/data` |
| Size | `1 GB` |

設定ファイルは `/var/data/settings.json` に作成されます。ディスクのマウント先と
`APP_SETTINGS_PATH` が一致していないと、設定が再起動後に消えます。

## Freeインスタンスを使う場合

動作確認だけなら、`render.yaml` の次の部分を変更できます。

```yaml
plan: free
```

ただし、Free Web Serviceでは永続ディスクを使用できないため、`disk` セクションを削除し、
`APP_SETTINGS_PATH` を `/tmp/settings.json` などへ変更するか、この環境変数自体を削除します。

Freeインスタンスには次の制限があります。

- 15分間アクセスがないとスピンダウンする
- 再起動、再デプロイ、スピンダウンでローカル設定ファイルが消える
- 永続ディスクを追加できない

設定画面で登録したWordPress URLと記事の型が消えるため、本アプリではStarter +
永続ディスクを推奨します。

Render公式のFree制限:
[Deploy for Free](https://render.com/docs/free)

## デプロイ後の動作確認

次の順で確認します。

1. `/health` がHTTP 200を返す
2. トップページがBasic認証なしではHTTP 401を返す
3. Basic認証後に3つのタブが表示される
4. 設定画面でWordPress URLと記事の型を保存できる
5. 再読み込み後も設定が残る
6. 公開記事URLからプレビューを作成できる
7. WordPressへ下書き保存できる
8. WordPress管理画面でステータスが「下書き」になっている

最初の確認では、公開しても問題ないテスト記事を利用してください。

## 自動デプロイ

RenderでGitHubリポジトリを接続した場合、通常は対象ブランチへのpushを検知して
自動デプロイできます。`main` へマージした変更が自動デプロイされる設定になっているか、
サービスのSettingsで確認してください。

永続ディスク付きサービスはデプロイ時に短い停止時間が発生します。設定JSONは
ディスク上に残ります。

## 環境変数を変更する場合

Render Dashboardのサービスを開き、`Environment` から変更します。Renderでは保存時に
再ビルド・再デプロイするか、既存ビルドを再デプロイするかを選択できます。

OpenAIキーやWordPressアプリケーションパスワードを変更した場合は、
新しい値でデプロイし直した後、古い認証情報を失効させてください。

## トラブルシューティング

### `No open ports detected`

Start Commandが次の内容になっているか確認します。

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

`127.0.0.1` へバインドするとRenderの外部通信を受けられません。

### ヘルスチェックが失敗する

- Health Check Pathが `/health` か確認する
- `/health` にBasic認証を要求していないか確認する
- `APP_USERNAME` と `APP_PASSWORD` の両方が設定されているか確認する
- Logsでアプリ起動時の例外を確認する

### 設定が再デプロイ後に消える

- Starter以上のインスタンスか確認する
- 永続ディスクが `/var/data` にマウントされているか確認する
- `APP_SETTINGS_PATH=/var/data/settings.json` か確認する
- 設定保存時のエラーがLogsに出ていないか確認する

### Basic認証が表示されない

`APP_USERNAME` と `APP_PASSWORD` の両方が設定されているか確認します。
Render上ではどちらか一方でも未設定の場合、アプリは安全のためHTTP 503を返します。
ローカル環境では両方とも未設定の場合に限り、開発しやすいよう認証を無効にします。

### WordPressへの保存に失敗する

- 設定画面のWordPress URLに `/wp-json` を付けていないか確認する
- `WP_USERNAME` がアプリケーションパスワードを発行したユーザーか確認する
- `WP_APP_PASSWORD` の値が正しいか確認する
- WordPress REST APIが外部からアクセス可能か確認する
- セキュリティプラグインがREST APIを遮断していないか確認する

### OpenAIで記事を生成できない

- `OPENAI_API_KEY` が設定されているか確認する
- APIキーが有効か確認する
- OpenAIの利用上限や請求設定を確認する
- `OPENAI_MODEL` が利用可能なモデルか確認する

## セキュリティ上の注意

- `.env` やAPIキーをGitHubへコミットしない
- `APP_PASSWORD` は他サービスと使い回さない
- 不要になったOpenAIキーとWordPressアプリケーションパスワードは失効させる
- Render Logsへ秘密情報を出力しない
- `onrender.com` URLを知っているだけでは利用できないよう、Basic認証を必ず有効にする
- WordPress側では必要最小限の権限を持つ専用ユーザーの利用を検討する
