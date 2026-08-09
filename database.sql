CREATE DATABASE IF NOT EXISTS watch_read
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE watch_read;


CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE media_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    media_type VARCHAR(30) NOT NULL,
    description TEXT,
    genre VARCHAR(100),
    release_year SMALLINT UNSIGNED,
    cover_url VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE user_library (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    media_id INT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'planned',
    rating TINYINT UNSIGNED,
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT unique_user_media
        UNIQUE (user_id, media_id),

    CONSTRAINT fk_library_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_library_media
        FOREIGN KEY (media_id)
        REFERENCES media_items(id)
        ON DELETE CASCADE
);