# 📅 Task & Habit Dashboard (DBSQL)

Flask と PostgreSQL を活用した、タスク管理および習慣追跡アプリケーションです。
カレンダー上でタスクの期限や習慣の継続状況を直感的に把握できるよう設計されています。

## ✨ 主な機能

### 1. ダイナミック・カレンダー
- `FullCalendar` を統合。月を跨いでもタスクと習慣が自動で表示されます。
- 表示期間に合わせて動的にイベントを取得するため、動作がスムーズです。

### 2. インテリジェントな習慣追跡
- **継続日数（ストリーク）表示**: 習慣を達成するごとに 🔥 マークと継続日数がカウントされます。
- **曜日指定機能**: 自分のライフスタイルに合わせて、特定の曜日だけの習慣を設定できます。

### 3. カラーカスタマイズ機能
- タスクや習慣ごとに好きな色を設定可能。
- よく使う色をお気に入り登録でき、不要になったら**右クリックで削除**して整理できます。

### 4. 緊急タスク通知
- 期限が迫っているタスクがある場合、ホーム画面に強調されたアラートが表示されます。

## 🛠 技術スタック
- **Backend**: Python / Flask
- **Database**: PostgreSQL / SQLAlchemy
- **Frontend**: FullCalendar.js / JavaScript / CSS3
- **Container**: Docker / Docker Compose

## 🚀 クイックスタート (Docker)

```bash
# リポジトリをクローン
git clone [https://github.com/taxsjet/DBSQL.git](https://github.com/taxsjet/DBSQL.git)
cd DBSQL

# コンテナの起動
docker-compose up --build
