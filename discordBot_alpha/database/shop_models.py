from datetime import datetime
from config.database import DatabaseManager
from database.models import BaseModel

class ShopModel(BaseModel):
    """
    Model for managing purchasable items in the shop.
    """
    
    async def get_purchasable_roles(self, guild_id: int):
        """
        Get all purchasable roles for a guild.
        
        Args:
            guild_id (int): The guild ID
            
        Returns:
            list: List of purchasable roles
        """
        query = """
            SELECT * FROM purchasable_roles 
            WHERE guild_id = %s AND is_active = TRUE
            ORDER BY price ASC
        """
        return await self.execute_query(query, (guild_id,))
        
    async def get_purchasable_role(self, guild_id: int, role_id: int):
        """
        Get a specific purchasable role.
        
        Args:
            guild_id (int): The guild ID
            role_id (int): The role ID
            
        Returns:
            dict or None: The role information, or None if not found
        """
        query = """
            SELECT * FROM purchasable_roles 
            WHERE guild_id = %s AND role_id = %s AND is_active = TRUE
        """
        results = await self.execute_query(query, (guild_id, role_id))
        return results[0] if results else None
        
    async def add_purchasable_role(self, guild_id: int, role_id: int, role_name: str, price: int, description: str = None):
        """
        Add a purchasable role.
        
        Args:
            guild_id (int): The guild ID
            role_id (int): The role ID
            role_name (str): The role name
            price (int): The price in points
            description (str, optional): Role description
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = """
                INSERT INTO purchasable_roles 
                (guild_id, role_id, role_name, price, description) 
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                role_name = %s,
                price = %s,
                description = %s,
                is_active = TRUE,
                updated_at = CURRENT_TIMESTAMP
            """
            await self.execute_query(
                query, 
                (guild_id, role_id, role_name, price, description, 
                 role_name, price, description),
                fetch=False
            )
            return True
        except Exception as e:
            print(f"Error adding purchasable role: {e}")
            return False
            
    async def remove_purchasable_role(self, guild_id: int, role_id: int):
        """
        Remove a purchasable role.
        
        Args:
            guild_id (int): The guild ID
            role_id (int): The role ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = """
                UPDATE purchasable_roles 
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = %s AND role_id = %s
            """
            await self.execute_query(query, (guild_id, role_id), fetch=False)
            return True
        except Exception as e:
            print(f"Error removing purchasable role: {e}")
            return False
            
    async def get_purchasable_channels(self, guild_id: int):
        """
        Get all purchasable channels for a guild.
        
        Args:
            guild_id (int): The guild ID
            
        Returns:
            list: List of purchasable channels
        """
        query = """
            SELECT * FROM purchasable_channels 
            WHERE guild_id = %s AND is_active = TRUE
            ORDER BY price ASC
        """
        return await self.execute_query(query, (guild_id,))
        
    async def get_purchasable_channel(self, guild_id: int, channel_id: int):
        """
        Get a specific purchasable channel.
        
        Args:
            guild_id (int): The guild ID
            channel_id (int): The channel ID
            
        Returns:
            dict or None: The channel information, or None if not found
        """
        query = """
            SELECT * FROM purchasable_channels 
            WHERE guild_id = %s AND channel_id = %s AND is_active = TRUE
        """
        results = await self.execute_query(query, (guild_id, channel_id))
        return results[0] if results else None
        
    async def add_purchasable_channel(self, guild_id: int, channel_id: int, channel_name: str, 
                                     price: int, access_role_id: int, description: str = None):
        """
        Add a purchasable channel.
        
        Args:
            guild_id (int): The guild ID
            channel_id (int): The channel ID
            channel_name (str): The channel name
            price (int): The price in points
            access_role_id (int): The role ID that grants access to the channel
            description (str, optional): Channel description
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = """
                INSERT INTO purchasable_channels 
                (guild_id, channel_id, channel_name, price, access_role_id, description) 
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                channel_name = %s,
                price = %s,
                access_role_id = %s,
                description = %s,
                is_active = TRUE,
                updated_at = CURRENT_TIMESTAMP
            """
            await self.execute_query(
                query, 
                (guild_id, channel_id, channel_name, price, access_role_id, description, 
                 channel_name, price, access_role_id, description),
                fetch=False
            )
            return True
        except Exception as e:
            print(f"Error adding purchasable channel: {e}")
            return False
            
    async def remove_purchasable_channel(self, guild_id: int, channel_id: int):
        """
        Remove a purchasable channel.
        
        Args:
            guild_id (int): The guild ID
            channel_id (int): The channel ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = """
                UPDATE purchasable_channels 
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = %s AND channel_id = %s
            """
            await self.execute_query(query, (guild_id, channel_id), fetch=False)
            return True
        except Exception as e:
            print(f"Error removing purchasable channel: {e}")
            return False
            
    async def purchase_role(self, user_id: int, guild_id: int, role_id: int):
        """
        Record a role purchase by a user.
        
        Args:
            user_id (int): The user's ID
            guild_id (int): The guild ID
            role_id (int): The role ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = """
                INSERT INTO user_purchased_roles 
                (user_id, guild_id, role_id) 
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                purchased_at = CURRENT_TIMESTAMP,
                expires_at = NULL
            """
            await self.execute_query(query, (user_id, guild_id, role_id), fetch=False)
            return True
        except Exception as e:
            print(f"Error recording role purchase: {e}")
            return False
            
    async def purchase_channel(self, user_id: int, guild_id: int, channel_id: int):
        """
        Record a channel purchase by a user.
        
        Args:
            user_id (int): The user's ID
            guild_id (int): The guild ID
            channel_id (int): The channel ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = """
                INSERT INTO user_purchased_channels 
                (user_id, guild_id, channel_id) 
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                purchased_at = CURRENT_TIMESTAMP,
                expires_at = NULL
            """
            await self.execute_query(query, (user_id, guild_id, channel_id), fetch=False)
            return True
        except Exception as e:
            print(f"Error recording channel purchase: {e}")
            return False
            
    async def has_purchased_role(self, user_id: int, guild_id: int, role_id: int):
        """
        Check if a user has purchased a role.
        
        Args:
            user_id (int): The user's ID
            guild_id (int): The guild ID
            role_id (int): The role ID
            
        Returns:
            bool: True if the user has purchased the role, False otherwise
        """
        query = """
            SELECT * FROM user_purchased_roles 
            WHERE user_id = %s AND guild_id = %s AND role_id = %s
            AND (expires_at IS NULL OR expires_at > NOW())
        """
        results = await self.execute_query(query, (user_id, guild_id, role_id))
        return bool(results)
        
    async def has_purchased_channel(self, user_id: int, guild_id: int, channel_id: int):
        """
        Check if a user has purchased access to a channel.
        
        Args:
            user_id (int): The user's ID
            guild_id (int): The guild ID
            channel_id (int): The channel ID
            
        Returns:
            bool: True if the user has purchased access to the channel, False otherwise
        """
        query = """
            SELECT * FROM user_purchased_channels 
            WHERE user_id = %s AND guild_id = %s AND channel_id = %s
            AND (expires_at IS NULL OR expires_at > NOW())
        """
        results = await self.execute_query(query, (user_id, guild_id, channel_id))
        return bool(results)