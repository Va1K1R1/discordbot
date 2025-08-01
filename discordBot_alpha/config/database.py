import mysql.connector
import mysql.connector.pooling
import sqlite3
import asyncio
import os
import time
from config.settings import Settings
import logging

class DatabaseManager:
    """
    Database connection manager for MySQL or SQLite.
    Provides connection pooling and async query execution.
    """
    
    def __init__(self):
        self.pool = None
        self.sqlite_connection = None
        self.db_type = Settings.DB_TYPE
        self.logger = logging.getLogger('discord_bot.database')
        self.query_cache = {}
        self.cache_ttl = 60  # Cache time-to-live in seconds
        
    async def initialize(self):
        """Initialize the database connection."""
        try:
            if self.db_type == 'sqlite':
                await self.initialize_sqlite()
            else:
                await self.initialize_mysql()
                
            # Test connection
            await self.execute_query("SELECT 1")
            self.logger.info(f"Database connection test successful (using {self.db_type})")
            
            # Run migrations
            await self.run_migrations()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
            
    async def initialize_mysql(self):
        """Initialize MySQL connection pool."""
        # Create connection pool with configurable size
        self.pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="discord_bot_pool",
            pool_size=Settings.DB_POOL_SIZE,
            host=Settings.DB_HOST,
            port=Settings.DB_PORT,
            user=Settings.DB_USER,
            password=Settings.DB_PASSWORD,
            database=Settings.DB_NAME
        )
        self.logger.info(f"MySQL connection pool initialized (pool size: {Settings.DB_POOL_SIZE})")
        
    async def initialize_sqlite(self):
        """Initialize SQLite connection."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(Settings.DB_SQLITE_PATH), exist_ok=True)
        
        # Create connection
        loop = asyncio.get_event_loop()
        self.sqlite_connection = await loop.run_in_executor(
            None,
            lambda: sqlite3.connect(Settings.DB_SQLITE_PATH, check_same_thread=False)
        )
        
        # Enable foreign keys
        cursor = self.sqlite_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()
        
        self.logger.info(f"SQLite connection initialized (path: {Settings.DB_SQLITE_PATH})")
    
    async def run_migrations(self):
        """Run database migrations from migrations.sql file."""
        try:
            # Check if we need to update existing tables
            await self.check_and_update_schema()
            
            migrations_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'migrations.sql')
            
            if os.path.exists(migrations_path):
                with open(migrations_path, 'r', encoding='utf-8') as f:
                    migration_sql = f.read()
                
                # Split by semicolons and execute each statement
                statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
                
                for statement in statements:
                    if statement:
                        await self.execute_query(statement, fetch=False)
                
                self.logger.info("Database migrations completed successfully")
            else:
                self.logger.warning("migrations.sql file not found")
                
        except Exception as e:
            self.logger.error(f"Failed to run migrations: {e}")
            raise
    
    async def check_and_update_schema(self):
        """Check existing schema and update if necessary."""
        try:
            # Check if message_logs table exists
            result = await self.execute_query("""
                SELECT COUNT(*) as count FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = 'message_logs'
            """, (Settings.DB_NAME,))
            
            if result and result[0]['count'] > 0:
                # Table exists, check if it has the required columns
                columns = await self.execute_query("""
                    SELECT COLUMN_NAME FROM information_schema.columns 
                    WHERE table_schema = %s AND table_name = 'message_logs'
                """, (Settings.DB_NAME,))
                
                existing_columns = [col['COLUMN_NAME'] for col in columns]
                
                # Add missing columns
                if 'channel_name' not in existing_columns:
                    await self.execute_query(
                        "ALTER TABLE message_logs ADD COLUMN channel_name VARCHAR(100) NOT NULL DEFAULT ''",
                        fetch=False
                    )
                    self.logger.info("Added channel_name column to message_logs")
                
                if 'guild_id' not in existing_columns:
                    await self.execute_query(
                        "ALTER TABLE message_logs ADD COLUMN guild_id BIGINT NOT NULL DEFAULT 0",
                        fetch=False
                    )
                    self.logger.info("Added guild_id column to message_logs")
                
                # Rename columns if they exist with old names
                if 'user_id' in existing_columns and 'author_id' not in existing_columns:
                    await self.execute_query(
                        "ALTER TABLE message_logs CHANGE COLUMN user_id author_id BIGINT NOT NULL",
                        fetch=False
                    )
                    self.logger.info("Renamed user_id to author_id in message_logs")
                
                if 'username' in existing_columns and 'author_name' not in existing_columns:
                    await self.execute_query(
                        "ALTER TABLE message_logs CHANGE COLUMN username author_name VARCHAR(100) NOT NULL",
                        fetch=False
                    )
                    self.logger.info("Renamed username to author_name in message_logs")
                
        except Exception as e:
            self.logger.error(f"Error checking/updating schema: {e}")
            # Continue with normal migration process
            
    async def execute_query(self, query, params=None, fetch=True, use_cache=False):
        """
        Execute a SQL query asynchronously.
        
        Args:
            query (str): SQL query to execute
            params (tuple, optional): Parameters for the query
            fetch (bool): Whether to fetch results (for SELECT queries)
            use_cache (bool): Whether to use query cache for SELECT queries
            
        Returns:
            list: Query results (for SELECT queries)
            int: Row count (for INSERT/UPDATE/DELETE queries)
        """
        # Check if database is initialized
        if self.db_type == 'sqlite' and not self.sqlite_connection:
            raise ValueError("SQLite database not initialized. Call initialize() first.")
        elif self.db_type != 'sqlite' and not self.pool:
            raise ValueError("MySQL database not initialized. Call initialize() first.")
            
        # Check cache for SELECT queries
        if fetch and use_cache and query.strip().upper().startswith('SELECT'):
            cache_key = f"{query}:{str(params)}"
            if cache_key in self.query_cache:
                cache_entry = self.query_cache[cache_key]
                if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                    self.logger.debug(f"Cache hit for query: {query}")
                    return cache_entry['data']
        
        # Execute query based on database type
        if self.db_type == 'sqlite':
            return await self._execute_sqlite_query(query, params, fetch)
        else:
            return await self._execute_mysql_query(query, params, fetch, use_cache)
    
    async def _execute_sqlite_query(self, query, params=None, fetch=True):
        """Execute a query on SQLite database."""
        loop = asyncio.get_event_loop()
        cursor = None
        
        try:
            # Convert MySQL placeholders (%) to SQLite placeholders (?)
            query = query.replace('%s', '?')
            
            # Execute query
            cursor = self.sqlite_connection.cursor()
            await loop.run_in_executor(
                None,
                lambda: cursor.execute(query, params or ())
            )
            
            if fetch:
                # Fetch results for SELECT queries
                rows = await loop.run_in_executor(
                    None,
                    lambda: cursor.fetchall()
                )
                
                # Convert to dictionary format like MySQL
                columns = [column[0] for column in cursor.description]
                result = [dict(zip(columns, row)) for row in rows]
                return result
            else:
                # For INSERT/UPDATE/DELETE queries
                await loop.run_in_executor(
                    None,
                    lambda: self.sqlite_connection.commit()
                )
                return cursor.rowcount
                
        except Exception as e:
            self.logger.error(f"SQLite query error: {e}")
            self.logger.error(f"Query: {query}")
            self.logger.error(f"Params: {params}")
            await loop.run_in_executor(
                None,
                lambda: self.sqlite_connection.rollback()
            )
            raise
            
        finally:
            if cursor:
                cursor.close()
    
    async def _execute_mysql_query(self, query, params=None, fetch=True, use_cache=False):
        """Execute a query on MySQL database."""
        connection = self.pool.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            # Execute query in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                lambda: cursor.execute(query, params)
            )
            
            if fetch:
                # Fetch results for SELECT queries
                result = await loop.run_in_executor(
                    None,
                    lambda: cursor.fetchall()
                )
                
                # Cache result if requested
                if use_cache and query.strip().upper().startswith('SELECT'):
                    cache_key = f"{query}:{str(params)}"
                    self.query_cache[cache_key] = {
                        'data': result,
                        'timestamp': time.time()
                    }
                    
                    # Cleanup old cache entries
                    self._cleanup_cache()
                    
                return result
            else:
                # For INSERT/UPDATE/DELETE queries
                connection.commit()
                return cursor.rowcount
                
        except Exception as e:
            self.logger.error(f"MySQL query error: {e}")
            self.logger.error(f"Query: {query}")
            self.logger.error(f"Params: {params}")
            connection.rollback()
            raise
            
        finally:
            cursor.close()
            connection.close()
    
    def _cleanup_cache(self):
        """Clean up expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.query_cache.items()
            if current_time - entry['timestamp'] > self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.query_cache[key]
            
    async def execute_many(self, query, params_list):
        """
        Execute a batch SQL query with multiple parameter sets.
        
        Args:
            query (str): SQL query to execute
            params_list (list): List of parameter tuples
            
        Returns:
            int: Total row count affected
        """
        if self.db_type == 'sqlite':
            return await self._execute_many_sqlite(query, params_list)
        else:
            return await self._execute_many_mysql(query, params_list)
    
    async def _execute_many_sqlite(self, query, params_list):
        """Execute a batch query on SQLite database."""
        loop = asyncio.get_event_loop()
        cursor = None
        
        try:
            # Convert MySQL placeholders (%) to SQLite placeholders (?)
            query = query.replace('%s', '?')
            
            # Execute query
            cursor = self.sqlite_connection.cursor()
            await loop.run_in_executor(
                None,
                lambda: cursor.executemany(query, params_list)
            )
            
            await loop.run_in_executor(
                None,
                lambda: self.sqlite_connection.commit()
            )
            return cursor.rowcount
            
        except Exception as e:
            self.logger.error(f"SQLite batch query error: {e}")
            self.logger.error(f"Query: {query}")
            await loop.run_in_executor(
                None,
                lambda: self.sqlite_connection.rollback()
            )
            raise
            
        finally:
            if cursor:
                cursor.close()
    
    async def _execute_many_mysql(self, query, params_list):
        """Execute a batch query on MySQL database."""
        if not self.pool:
            raise ValueError("Database not initialized. Call initialize() first.")
            
        connection = self.pool.get_connection()
        cursor = connection.cursor()
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: cursor.executemany(query, params_list)
            )
            
            connection.commit()
            return cursor.rowcount
            
        except Exception as e:
            self.logger.error(f"MySQL batch query error: {e}")
            connection.rollback()
            raise
            
        finally:
            cursor.close()
            connection.close()