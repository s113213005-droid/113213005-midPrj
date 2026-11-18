-- user
CREATE TABLE IF NOT EXISTS users (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    passHash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL
        CHECK (role IN ('author', 'editor'))
);

-- 投稿資料表
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    author_id INTEGER NOT NULL REFERENCES users(id),
    category VARCHAR(100) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT '編輯中'
        CHECK (status IN ('編輯中', '審查中', '已通過'))
);
