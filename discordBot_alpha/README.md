# Multi-Feature Discord Bot

A feature-rich Discord bot with role-based permissions, point system, message management, logging, and more. Now with optimizations for Raspberry Pi deployment!

## Features

### Core Features
- **Role-based Permission System**: Admin, moderator, and user roles with different access levels
- **Point System**: Award points for user activity, with leaderboards and level progression
- **Message Management**: Schedule message deletions, bulk delete messages, and more
- **Comprehensive Logging**: Log all messages to database and/or dedicated Discord channel
- **Shop System**: Allow users to spend points on roles, items, or custom rewards
- **Gambling & Betting**: Fun mini-games for users to engage with

### Raspberry Pi Optimizations
This bot has been specially optimized to run efficiently on Raspberry Pi devices:

- **Database Flexibility**: Choose between MySQL and lightweight SQLite
- **Memory Optimization**: Selective cog loading and memory usage monitoring
- **CPU Usage Reduction**: Configurable background task intervals
- **SD Card Life Extension**: Optional file logging and optimized database operations
- **Auto-Configuration**: Automatic detection and optimization for Raspberry Pi

For detailed information about Raspberry Pi deployment:
- [Raspberry Pi Deployment Guide](RASPBERRY_PI_GUIDE.md) - Complete installation and setup instructions
- [Optimization Summary](RASPBERRY_PI_OPTIMIZATION_SUMMARY.md) - Technical details of all optimizations

## Requirements

- Python 3.8 or higher
- Discord.py 2.3.2 or higher
- Database: MySQL or SQLite
- See [requirements.txt](requirements.txt) for all dependencies

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/discord_bot.git
   cd discord_bot
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Create .env file**
   ```bash
   # Discord Bot Settings
   DISCORD_TOKEN=your_discord_token_here
   GUILD_ID=your_guild_id_here
   COMMAND_PREFIX=/
   
   # Database Settings (MySQL)
   DB_TYPE=mysql
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=discord_bot
   DB_PASSWORD=your_password_here
   DB_NAME=discord_bot_db
   
   # Role IDs
   ADMIN_ROLE_ID=your_admin_role_id
   MODERATOR_ROLE_ID=your_moderator_role_id
   TRUSTED_ROLE_ID=your_trusted_role_id
   BOT_OWNER_ID=your_user_id
   
   # Logging Settings
   LOG_LEVEL=INFO
   LOG_CHANNEL_ID=your_log_channel_id
   LOG_TO_FILE=true
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

## Configuration Options

### Standard Configuration
- `DISCORD_TOKEN`: Your Discord bot token
- `GUILD_ID`: Your Discord server ID
- `COMMAND_PREFIX`: Command prefix (default: `/`)
- `DB_TYPE`: Database type (`mysql` or `sqlite`)
- `LOG_LEVEL`: Logging level (`INFO`, `DEBUG`, `WARNING`, etc.)
- `LOG_TO_FILE`: Whether to log to file (`true` or `false`)

### Raspberry Pi Specific Configuration
- `LIGHTWEIGHT_MODE`: Enable lightweight mode (`true` or `false`)
- `ENABLED_COGS`: Comma-separated list of cogs to load
- `BACKGROUND_TASK_INTERVAL`: Interval in seconds for background tasks
- `DB_POOL_SIZE`: Database connection pool size
- `MEMORY_LIMIT_MB`: Memory usage limit in MB

## Commands

### Admin Commands
- `/권한확인 [user]` - Check user's permission level
- `/권한부여 [user] [role]` - Grant role to user
- `/포인트추가 [user] [amount] [reason]` - Add points to user

### Moderator Commands
- `/예약삭제 [message_id] [delay_minutes] [reason]` - Schedule message deletion
- `/삭제취소 [message_id]` - Cancel scheduled deletion
- `/청소 [amount] [user]` - Bulk delete messages

### User Commands
- `/포인트` - Check your points
- `/랭킹` - View points leaderboard
- `/도움말` - Show help message

## Development

### Project Structure
```
discord_bot/
├── main.py                 # Main entry point
├── config/                 # Configuration
│   ├── settings.py         # Settings management
│   └── database.py         # Database connection
├── cogs/                   # Feature modules
│   ├── permissions.py      # Permission system
│   ├── points.py           # Point system
│   ├── message_manager.py  # Message management
│   └── logging_system.py   # Logging system
├── utils/                  # Utilities
│   ├── helpers.py          # Helper functions
│   ├── decorators.py       # Command decorators
│   └── permissions.py      # Permission utilities
└── database/               # Database models
    ├── models.py           # Core models
    └── migrations.sql      # Database schema
```

### Adding New Features
1. Create a new cog in the `cogs/` directory
2. Add the cog to the `load_extensions()` method in `main.py`
3. Update the `ENABLED_COGS` list in your configuration if using selective loading

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Discord.py](https://github.com/Rapptz/discord.py) - The Discord API wrapper
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Environment variable management
- All contributors to this project