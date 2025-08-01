-- Additional tables for new features

-- Purchasable roles table
CREATE TABLE IF NOT EXISTS purchasable_roles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    role_name VARCHAR(100) NOT NULL,
    price INT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_role (guild_id, role_id),
    INDEX idx_guild_id (guild_id),
    INDEX idx_role_id (role_id),
    INDEX idx_price (price)
);

-- Purchasable channels table
CREATE TABLE IF NOT EXISTS purchasable_channels (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    channel_name VARCHAR(100) NOT NULL,
    price INT NOT NULL,
    description TEXT,
    access_role_id BIGINT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_channel (guild_id, channel_id),
    INDEX idx_guild_id (guild_id),
    INDEX idx_channel_id (channel_id),
    INDEX idx_price (price)
);

-- User purchased roles table
CREATE TABLE IF NOT EXISTS user_purchased_roles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    UNIQUE KEY unique_user_role (user_id, guild_id, role_id),
    INDEX idx_user_id (user_id),
    INDEX idx_guild_id (guild_id),
    INDEX idx_role_id (role_id)
);

-- User purchased channels table
CREATE TABLE IF NOT EXISTS user_purchased_channels (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    UNIQUE KEY unique_user_channel (user_id, guild_id, channel_id),
    INDEX idx_user_id (user_id),
    INDEX idx_guild_id (guild_id),
    INDEX idx_channel_id (channel_id)
);

-- Gambling box types table
CREATE TABLE IF NOT EXISTS gambling_box_types (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_box_name (guild_id, name),
    INDEX idx_guild_id (guild_id),
    INDEX idx_price (price)
);

-- Gambling rewards table
CREATE TABLE IF NOT EXISTS gambling_rewards (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    box_type_id BIGINT NOT NULL,
    reward_type ENUM('POINTS', 'ROLE', 'ITEM') NOT NULL,
    reward_value VARCHAR(100) NOT NULL,
    reward_amount INT DEFAULT 0,
    probability FLOAT NOT NULL, -- Value between 0 and 1
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_box_type_id (box_type_id),
    INDEX idx_reward_type (reward_type),
    FOREIGN KEY (box_type_id) REFERENCES gambling_box_types(id) ON DELETE CASCADE
);

-- Gambling history table
CREATE TABLE IF NOT EXISTS gambling_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    box_type_id BIGINT NOT NULL,
    reward_id BIGINT NOT NULL,
    points_spent INT NOT NULL,
    points_won INT DEFAULT 0,
    role_id BIGINT DEFAULT NULL,
    item_name VARCHAR(100) DEFAULT NULL,
    gambled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_guild_id (guild_id),
    INDEX idx_box_type_id (box_type_id),
    INDEX idx_reward_id (reward_id),
    INDEX idx_gambled_at (gambled_at),
    FOREIGN KEY (box_type_id) REFERENCES gambling_box_types(id) ON DELETE CASCADE,
    FOREIGN KEY (reward_id) REFERENCES gambling_rewards(id) ON DELETE CASCADE
);

-- Betting events table
CREATE TABLE IF NOT EXISTS betting_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    creator_id BIGINT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status ENUM('OPEN', 'LOCKED', 'SETTLED', 'CANCELLED') DEFAULT 'OPEN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    locked_at TIMESTAMP NULL,
    settled_at TIMESTAMP NULL,
    winning_option_id BIGINT NULL,
    INDEX idx_guild_id (guild_id),
    INDEX idx_creator_id (creator_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

-- Betting options table
CREATE TABLE IF NOT EXISTS betting_options (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    odds FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_event_id (event_id),
    FOREIGN KEY (event_id) REFERENCES betting_events(id) ON DELETE CASCADE
);

-- User bets table
CREATE TABLE IF NOT EXISTS user_bets (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    event_id BIGINT NOT NULL,
    option_id BIGINT NOT NULL,
    amount INT NOT NULL,
    potential_winnings INT NOT NULL,
    status ENUM('ACTIVE', 'WON', 'LOST', 'REFUNDED') DEFAULT 'ACTIVE',
    placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settled_at TIMESTAMP NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_event_id (event_id),
    INDEX idx_option_id (option_id),
    INDEX idx_status (status),
    FOREIGN KEY (event_id) REFERENCES betting_events(id) ON DELETE CASCADE,
    FOREIGN KEY (option_id) REFERENCES betting_options(id) ON DELETE CASCADE
);