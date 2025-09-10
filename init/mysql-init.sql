-- MySQL initialization script for Private Chat Interface

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS chat_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Use the database
USE chat_db;

-- Grant all privileges to chat_user
GRANT ALL PRIVILEGES ON chat_db.* TO 'chat_user'@'%';
FLUSH PRIVILEGES;

-- Set timezone
SET GLOBAL time_zone = '+00:00';
