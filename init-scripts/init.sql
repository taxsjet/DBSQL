-- 1. ユーザーテーブル
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. タスクテーブル
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    due_date TIMESTAMP NOT NULL,
    notification_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 習慣マスターテーブル
CREATE TABLE IF NOT EXISTS habits (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    goal_days_per_week INTEGER DEFAULT 7,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 習慣の実行ログ
CREATE TABLE IF NOT EXISTS habit_logs (
    id SERIAL PRIMARY KEY,
    habit_id INTEGER REFERENCES habits(id) ON DELETE CASCADE,
    completed_at DATE DEFAULT CURRENT_DATE,
    UNIQUE(habit_id, completed_at)
);

-- 5. サンプルデータの挿入
-- ユーザー登録
INSERT INTO users (username, email) VALUES 
('admin', 'admin@example.com'),
('testuser', 'testuser@example.com');

-- タスク登録（ユーザー1: admin）
INSERT INTO tasks (user_id, title, due_date) VALUES 
(1, '明日のレポート提出', CURRENT_TIMESTAMP + INTERVAL '1 day');

-- 習慣登録（ユーザー1: admin）
INSERT INTO habits (user_id, title) VALUES (1, 'スクワット20回');

-- 習慣実行ログ登録
INSERT INTO habit_logs (habit_id, completed_at) VALUES (1, CURRENT_DATE);