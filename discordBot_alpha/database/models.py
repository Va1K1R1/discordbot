from datetime import datetime
import json
from config.database import DatabaseManager

class BaseModel:
    """
    Base model class with common database operations.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        
    async def execute_query(self, query, params=None, fetch=True):
        """Execute a database query."""
        return await self.db.execute_query(query, params, fetch)
        
    async def execute_many(self, query, params_list):
        """Execute a batch database query."""
        return await self.db.execute_many(query, params_list)

class UserPointsModel(BaseModel):
    """
    Model for managing user points.
    """
    
    async def get_user_points(self, user_id: int):
        """
        Get a user's points information.
        
        Args:
            user_id (int): The user's ID
            
        Returns:
            dict or None: The user's points information, or None if not found
        """
        query = "SELECT * FROM user_points WHERE user_id = %s"
        results = await self.execute_query(query, (user_id,))
        return results[0] if results else None
        
    async def add_points(self, user_id: int, username: str, amount: int, reason: str, admin_id: int = None):
        """
        Add points to a user.
        
        Args:
            user_id (int): The user's ID
            username (str): The user's name
            amount (int): The amount of points to add
            reason (str): The reason for adding points
            admin_id (int, optional): The ID of the admin who added the points
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Insert or update user points
            query = """
                INSERT INTO user_points (user_id, username, points, total_earned) 
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                points = points + %s,
                total_earned = total_earned + %s,
                username = %s,
                updated_at = CURRENT_TIMESTAMP
            """
            await self.execute_query(
                query, 
                (user_id, username, amount, amount, amount, amount, username),
                fetch=False
            )
            
            # Record transaction
            transaction_type = 'ADMIN_ADD' if admin_id else 'EARN'
            query = """
                INSERT INTO point_transactions 
                (user_id, transaction_type, amount, reason, admin_id)
                VALUES (%s, %s, %s, %s, %s)
            """
            await self.execute_query(
                query,
                (user_id, transaction_type, amount, reason, admin_id),
                fetch=False
            )
            
            return True
        except Exception as e:
            print(f"Error adding points: {e}")
            return False
            
    async def remove_points(self, user_id: int, amount: int, reason: str, admin_id: int = None):
        """
        Remove points from a user.
        
        Args:
            user_id (int): The user's ID
            amount (int): The amount of points to remove
            reason (str): The reason for removing points
            admin_id (int, optional): The ID of the admin who removed the points
            
        Returns:
            tuple: (success, message)
        """
        try:
            # Check if user has enough points
            user_points = await self.get_user_points(user_id)
            if not user_points or user_points['points'] < amount:
                return False, "포인트가 부족합니다."
                
            # Update user points
            query = """
                UPDATE user_points 
                SET points = points - %s, 
                    total_spent = total_spent + %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """
            await self.execute_query(query, (amount, amount, user_id), fetch=False)
            
            # Record transaction
            transaction_type = 'ADMIN_REMOVE' if admin_id else 'SPEND'
            query = """
                INSERT INTO point_transactions 
                (user_id, transaction_type, amount, reason, admin_id)
                VALUES (%s, %s, %s, %s, %s)
            """
            await self.execute_query(
                query,
                (user_id, transaction_type, amount, reason, admin_id),
                fetch=False
            )
            
            return True, "포인트가 성공적으로 차감되었습니다."
        except Exception as e:
            print(f"Error removing points: {e}")
            return False, f"오류 발생: {str(e)}"
            
    async def get_leaderboard(self, limit: int = 10):
        """
        Get the points leaderboard.
        
        Args:
            limit (int): The maximum number of users to return
            
        Returns:
            list: The leaderboard data
        """
        query = """
            SELECT user_id, username, points, level 
            FROM user_points 
            ORDER BY points DESC 
            LIMIT %s
        """
        return await self.execute_query(query, (limit,))
        
    async def update_experience(self, user_id: int, username: str, exp_amount: int):
        """
        Update a user's experience and check for level up.
        
        Args:
            user_id (int): The user's ID
            username (str): The user's name
            exp_amount (int): The amount of experience to add
            
        Returns:
            dict or None: Level up information if the user leveled up, None otherwise
        """
        # Get current user data
        user_data = await self.get_user_points(user_id)
        
        if not user_data:
            # Create new user
            query = """
                INSERT INTO user_points (user_id, username, experience) 
                VALUES (%s, %s, %s)
            """
            await self.execute_query(query, (user_id, username, exp_amount), fetch=False)
            current_exp = exp_amount
            old_level = 1
        else:
            # Update existing user
            current_exp = user_data['experience'] + exp_amount
            old_level = user_data['level']
            
            query = """
                UPDATE user_points 
                SET experience = experience + %s,
                    username = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """
            await self.execute_query(query, (exp_amount, username, user_id), fetch=False)
        
        # Calculate new level
        new_level = self.calculate_level(current_exp)
        
        # Check for level up
        if new_level > old_level:
            # Update level
            query = "UPDATE user_points SET level = %s WHERE user_id = %s"
            await self.execute_query(query, (new_level, user_id), fetch=False)
            
            return {
                'old_level': old_level,
                'new_level': new_level,
                'user_id': user_id,
                'username': username
            }
            
        return None
        
    def calculate_level(self, experience: int) -> int:
        """
        Calculate level based on experience.
        
        Args:
            experience (int): The user's experience
            
        Returns:
            int: The calculated level
        """
        # Simple level calculation formula: level = sqrt(exp / 100) + 1
        import math
        return int(math.sqrt(experience / 100)) + 1

class MessageLogModel(BaseModel):
    """
    Model for logging messages.
    """
    
    async def log_message(self, message_id: int, channel_id: int, channel_name: str, 
                         author_id: int, author_name: str, content: str, 
                         guild_id: int, attachments=None, embeds=None, message_type='text'):
        """
        Log a message to the database.
        
        Args:
            message_id (int): The message ID
            channel_id (int): The channel ID
            channel_name (str): The channel name
            author_id (int): The author's ID
            author_name (str): The author's name
            content (str): The message content
            guild_id (int): The guild/server ID
            attachments (list, optional): List of attachments
            embeds (list, optional): List of embeds
            message_type (str, optional): The message type
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert attachments and embeds to JSON
            attachments_json = json.dumps(attachments) if attachments else None
            embeds_json = json.dumps(embeds) if embeds else None
            
            query = """
                INSERT INTO message_logs 
                (message_id, channel_id, channel_name, guild_id, author_id, author_name, 
                 content, attachments, embeds, message_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            await self.execute_query(
                query, 
                (message_id, channel_id, channel_name, guild_id, author_id, author_name, 
                 content, attachments_json, embeds_json, message_type),
                fetch=False
            )
            
            return True
        except Exception as e:
            print(f"Error logging message: {e}")
            return False
            
    async def log_event(self, event_type: str, details, user_id: int = None, channel_id: int = None):
        """
        Log an event to the database.
        
        Args:
            event_type (str): The type of event
            details (dict): Event details
            user_id (int, optional): The user's ID
            channel_id (int, optional): The channel ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            details_json = json.dumps(details)
            
            query = """
                INSERT INTO event_logs (event_type, user_id, channel_id, details)
                VALUES (%s, %s, %s, %s)
            """
            await self.execute_query(
                query, 
                (event_type, user_id, channel_id, details_json),
                fetch=False
            )
            
            return True
        except Exception as e:
            print(f"Error logging event: {e}")
            return False
            
    async def search_logs(self, user_id=None, channel_id=None, content_search=None, 
                         start_time=None, end_time=None, limit=100):
        """
        Search message logs.
        
        Args:
            user_id (int, optional): Filter by user ID
            channel_id (int, optional): Filter by channel ID
            content_search (str, optional): Search in message content
            start_time (datetime, optional): Start time for search
            end_time (datetime, optional): End time for search
            limit (int, optional): Maximum number of results
            
        Returns:
            list: The search results
        """
        conditions = []
        params = []
        
        if user_id:
            conditions.append("author_id = %s")
            params.append(user_id)
            
        if channel_id:
            conditions.append("channel_id = %s")
            params.append(channel_id)
            
        if content_search:
            conditions.append("content LIKE %s")
            params.append(f"%{content_search}%")
            
        if start_time:
            conditions.append("created_at >= %s")
            params.append(start_time)
            
        if end_time:
            conditions.append("created_at <= %s")
            params.append(end_time)
            
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT * FROM message_logs 
            WHERE {where_clause}
            ORDER BY created_at DESC 
            LIMIT %s
        """
        params.append(limit)
        
        return await self.execute_query(query, tuple(params))

class ScheduledDeletionModel(BaseModel):
    """
    Model for managing scheduled message deletions.
    """
    
    async def schedule_deletion(self, message_id: int, channel_id: int, 
                               delete_at: datetime, requester_id: int, reason: str = None):
        """
        Schedule a message for deletion.
        
        Args:
            message_id (int): The message ID
            channel_id (int): The channel ID
            delete_at (datetime): When to delete the message
            requester_id (int): The ID of the user who requested the deletion
            reason (str, optional): The reason for deletion
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = """
                INSERT INTO scheduled_deletions 
                (message_id, channel_id, delete_at, requester_id, reason)
                VALUES (%s, %s, %s, %s, %s)
            """
            await self.execute_query(
                query, 
                (message_id, channel_id, delete_at, requester_id, reason),
                fetch=False
            )
            
            return True
        except Exception as e:
            print(f"Error scheduling deletion: {e}")
            return False
            
    async def get_pending_deletions(self):
        """
        Get all pending scheduled deletions.
        
        Returns:
            list: Pending deletions
        """
        query = """
            SELECT * FROM scheduled_deletions 
            WHERE delete_at <= %s
            ORDER BY delete_at
        """
        return await self.execute_query(query, (datetime.now(),))
        
    async def remove_scheduled_deletion(self, message_id: int):
        """
        Remove a scheduled deletion.
        
        Args:
            message_id (int): The message ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = "DELETE FROM scheduled_deletions WHERE message_id = %s"
            result = await self.execute_query(query, (message_id,), fetch=False)
            return result > 0
        except Exception as e:
            print(f"Error removing scheduled deletion: {e}")
            return False

class ServerSettingsModel(BaseModel):
    """
    Model for managing server settings.
    """
    
    async def get_server_settings(self, guild_id: int):
        """
        Get server settings.
        
        Args:
            guild_id (int): The guild ID
            
        Returns:
            dict or None: The server settings, or None if not found
        """
        query = "SELECT * FROM server_settings WHERE guild_id = %s"
        results = await self.execute_query(query, (guild_id,))
        return results[0] if results else None
        
    async def update_server_settings(self, guild_id: int, settings: dict):
        """
        Update server settings.
        
        Args:
            guild_id (int): The guild ID
            settings (dict): The settings to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if settings exist
            existing = await self.get_server_settings(guild_id)
            
            if not existing:
                # Create new settings
                columns = ', '.join(settings.keys())
                placeholders = ', '.join(['%s'] * len(settings))
                values = tuple(settings.values())
                
                query = f"""
                    INSERT INTO server_settings (guild_id, {columns})
                    VALUES (%s, {placeholders})
                """
                await self.execute_query(query, (guild_id,) + values, fetch=False)
            else:
                # Update existing settings
                set_clause = ', '.join([f"{key} = %s" for key in settings.keys()])
                values = tuple(settings.values())
                
                query = f"""
                    UPDATE server_settings 
                    SET {set_clause}
                    WHERE guild_id = %s
                """
                await self.execute_query(query, values + (guild_id,), fetch=False)
                
            return True
        except Exception as e:
            print(f"Error updating server settings: {e}")
            return False