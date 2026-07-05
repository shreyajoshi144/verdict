-- Verdict Database Schema
-- Run this file to initialize the database

CREATE DATABASE IF NOT EXISTS verdict CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE verdict;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products cache table
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    website VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    original_price DECIMAL(10, 2),
    discount DECIMAL(5, 2) DEFAULT 0,
    rating DECIMAL(3, 2) DEFAULT 0,
    rating_count INT DEFAULT 0,
    image_url TEXT,
    product_url TEXT NOT NULL,
    brand VARCHAR(200),
    category VARCHAR(100),
    search_query VARCHAR(500),
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_search_query (search_query(100)),
    INDEX idx_website (website),
    INDEX idx_price (price)
);

-- Wishlist table
CREATE TABLE IF NOT EXISTS wishlist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_name VARCHAR(500) NOT NULL,
    website VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    discount DECIMAL(5, 2) DEFAULT 0,
    rating DECIMAL(3, 2) DEFAULT 0,
    image_url TEXT,
    product_url TEXT NOT NULL,
    brand VARCHAR(200),
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
);

-- Search history table
CREATE TABLE IF NOT EXISTS search_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    query VARCHAR(500) NOT NULL,
    filters JSON,
    result_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);

-- Budget plans table
CREATE TABLE IF NOT EXISTS budget_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    budget DECIMAL(10, 2) NOT NULL,
    category VARCHAR(200),
    description TEXT,
    ai_plan JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
);

-- Insert default demo user. Password is "verdict123" — change it after first login.
INSERT IGNORE INTO users (id, name, email, password_hash)
VALUES (1, 'Demo User', 'demo@verdict.ai', '$2b$12$1/8L94WfHpJn1JG6AugLweu2lMgaNpsCYbkhCJyciWyRn1OnPM3Z.');
