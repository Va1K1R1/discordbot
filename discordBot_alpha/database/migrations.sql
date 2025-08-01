-- Create database tables for Discord bot

-- User points table
CREATE TABLE IF NOT EXISTS user_points (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL,
    points INT DEFAULT 0,
    total_earned INT DEFAULT 0,
    total_spent INT DEFAULT 0,
    level INT DEFAULT 1,
    experience INT DEFAULT 0,
    last_message_time TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_points (points),
    INDEX idx_level (level)
);

-- Point transactions table
CREATE TABLE IF NOT EXISTS point_transactions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    transaction_type ENUM('EARN', 'SPEND', 'ADMIN_ADD', 'ADMIN_REMOVE') NOT NULL,
    amount INT NOT NULL,
    reason VARCHAR(255) NOT NULL,
    admin_id BIGINT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_transaction_type (transaction_type),
    INDEX idx_created_at (created_at)
);

-- Scheduled deletions table
CREATE TABLE IF NOT EXISTS scheduled_deletions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    message_id BIGINT NOT NULL UNIQUE,
    channel_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    requester_id BIGINT NOT NULL,
    delete_at DATETIME NOT NULL,
    reason VARCHAR(255) DEFAULT 'Scheduled deletion',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_message_id (message_id),
    INDEX idx_delete_at (delete_at),
    INDEX idx_guild_id (guild_id)
);

-- Message logs table (updated schema to match code)
CREATE TABLE IF NOT EXISTS message_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    message_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    channel_name VARCHAR(100) NOT NULL,
    guild_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    author_name VARCHAR(100) NOT NULL,
    content TEXT,
    attachments JSON,
    embeds JSON,
    message_type ENUM('SEND', 'EDIT', 'DELETE', 'text', 'image', 'file', 'embed') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_message_id (message_id),
    INDEX idx_channel_id (channel_id),
    INDEX idx_author_id (author_id),
    INDEX idx_created_at (created_at)
);

-- Server settings table
CREATE TABLE IF NOT EXISTS server_settings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL UNIQUE,
    prefix VARCHAR(10) DEFAULT '/',
    log_channel_id BIGINT NULL,
    welcome_channel_id BIGINT NULL,
    auto_role_id BIGINT NULL,
    settings JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_guild_id (guild_id)
);

-- User permissions table
CREATE TABLE IF NOT EXISTS user_permissions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    permission_level ENUM('RESTRICTED', 'MEMBER', 'TRUSTED', 'MODERATOR', 'ADMIN', 'OWNER') DEFAULT 'MEMBER',
    granted_by BIGINT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    UNIQUE KEY unique_user_guild (user_id, guild_id),
    INDEX idx_user_id (user_id),
    INDEX idx_guild_id (guild_id),
    INDEX idx_permission_level (permission_level)
);