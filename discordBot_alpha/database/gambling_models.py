from datetime import datetime
import random
from config.database import DatabaseManager
from database.models import BaseModel

class GamblingModel(BaseModel):
    """
    Model for managing gambling boxes and rewards.
    """
    
    async def get_box_types(self, guild_id: int):
        """
        Get all gambling box types for a guild.
        
        Args:
            guild_id (int): The guild ID
            
        Returns:
            list: List of gambling box types
        """
        query = """
            SELECT * FROM gambling_box_types 
            WHERE guild_id = %s AND is_active = TRUE
            ORDER BY price ASC
        """
        return await self.execute_query(query, (guild_id,))
        
    async def get_box_type(self, box_id: int):
        """
        Get a specific gambling box type.
        
        Args:
            box_id (int): The box type ID
            
        Returns:
            dict or None: The box type information, or None if not found
        """
        query = "SELECT * FROM gambling_box_types WHERE id = %s AND is_active = TRUE"
        results = await self.execute_query(query, (box_id,))
        return results[0] if results else None
        
    async def get_box_type_by_name(self, guild_id: int, name: str):
        """
        Get a specific gambling box type by name.
        
        Args:
            guild_id (int): The guild ID
            name (str): The box type name
            
        Returns:
            dict or None: The box type information, or None if not found
        """
        query = """
            SELECT * FROM gambling_box_types 
            WHERE guild_id = %s AND name = %s AND is_active = TRUE
        """
        results = await self.execute_query(query, (guild_id, name))
        return results[0] if results else None
        
    async def add_box_type(self, guild_id: int, name: str, price: int, description: str = None):
        """
        Add a gambling box type.
        
        Args:
            guild_id (int): The guild ID
            name (str): The box type name
            price (int): The price in points
            description (str, optional): Box description
            
        Returns:
            int or None: The box type ID if successful, None otherwise
        """
        try:
            query = """
                INSERT INTO gambling_box_types 
                (guild_id, name, price, description) 
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                price = %s,
                description = %s,
                is_active = TRUE,
                updated_at = CURRENT_TIMESTAMP
            """
            result = await self.execute_query(
                query, 
                (guild_id, name, price, description, price, description),
                fetch=True
            )
            
            # Get the ID of the inserted/updated box type
            if result and 'lastrowid' in result:
                return result['lastrowid']
                
            # If we didn't get the ID from the insert, look it up
            box_type = await self.get_box_type_by_name(guild_id, name)
            return box_type['id'] if box_type else None
            
        except Exception as e:
            print(f"Error adding gambling box type: {e}")
            return None
            
    async def remove_box_type(self, box_id: int):
        """
        Remove a gambling box type.
        
        Args:
            box_id (int): The box type ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = """
                UPDATE gambling_box_types 
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            await self.execute_query(query, (box_id,), fetch=False)
            return True
        except Exception as e:
            print(f"Error removing gambling box type: {e}")
            return False
            
    async def get_rewards(self, box_type_id: int):
        """
        Get all rewards for a gambling box type.
        
        Args:
            box_type_id (int): The box type ID
            
        Returns:
            list: List of rewards
        """
        query = "SELECT * FROM gambling_rewards WHERE box_type_id = %s"
        return await self.execute_query(query, (box_type_id,))
        
    async def add_reward(self, box_type_id: int, reward_type: str, reward_value: str, 
                        reward_amount: int, probability: float, description: str = None):
        """
        Add a reward to a gambling box type.
        
        Args:
            box_type_id (int): The box type ID
            reward_type (str): The reward type (POINTS, ROLE, ITEM)
            reward_value (str): The reward value (role ID for ROLE, item name for ITEM)
            reward_amount (int): The reward amount (points for POINTS)
            probability (float): The probability of getting this reward (0-1)
            description (str, optional): Reward description
            
        Returns:
            int or None: The reward ID if successful, None otherwise
        """
        try:
            query = """
                INSERT INTO gambling_rewards 
                (box_type_id, reward_type, reward_value, reward_amount, probability, description) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            result = await self.execute_query(
                query, 
                (box_type_id, reward_type, reward_value, reward_amount, probability, description),
                fetch=True
            )
            
            return result['lastrowid'] if result and 'lastrowid' in result else None
            
        except Exception as e:
            print(f"Error adding gambling reward: {e}")
            return None
            
    async def remove_reward(self, reward_id: int):
        """
        Remove a reward.
        
        Args:
            reward_id (int): The reward ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = "DELETE FROM gambling_rewards WHERE id = %s"
            await self.execute_query(query, (reward_id,), fetch=False)
            return True
        except Exception as e:
            print(f"Error removing gambling reward: {e}")
            return False
            
    async def get_random_reward(self, box_type_id: int):
        """
        Get a random reward from a gambling box type based on probabilities.
        
        Args:
            box_type_id (int): The box type ID
            
        Returns:
            dict or None: The reward information, or None if no rewards found
        """
        rewards = await self.get_rewards(box_type_id)
        if not rewards:
            return None
            
        # Calculate total probability
        total_probability = sum(reward['probability'] for reward in rewards)
        
        # Normalize probabilities if they don't sum to 1
        if total_probability != 1.0:
            for reward in rewards:
                reward['probability'] = reward['probability'] / total_probability
                
        # Select a random reward based on probability
        rand_val = random.random()
        cumulative_prob = 0
        
        for reward in rewards:
            cumulative_prob += reward['probability']
            if rand_val <= cumulative_prob:
                return reward
                
        # Fallback to the last reward if something went wrong
        return rewards[-1]
        
    async def record_gambling(self, user_id: int, guild_id: int, box_type_id: int, 
                             reward_id: int, points_spent: int, points_won: int = 0, 
                             role_id: int = None, item_name: str = None):
        """
        Record a gambling transaction.
        
        Args:
            user_id (int): The user's ID
            guild_id (int): The guild ID
            box_type_id (int): The box type ID
            reward_id (int): The reward ID
            points_spent (int): The points spent
            points_won (int, optional): The points won
            role_id (int, optional): The role ID if a role was won
            item_name (str, optional): The item name if an item was won
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = """
                INSERT INTO gambling_history 
                (user_id, guild_id, box_type_id, reward_id, points_spent, points_won, role_id, item_name) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            await self.execute_query(
                query, 
                (user_id, guild_id, box_type_id, reward_id, points_spent, points_won, role_id, item_name),
                fetch=False
            )
            return True
        except Exception as e:
            print(f"Error recording gambling history: {e}")
            return False
            
    async def get_user_gambling_history(self, user_id: int, limit: int = 10):
        """
        Get a user's gambling history.
        
        Args:
            user_id (int): The user's ID
            limit (int, optional): The maximum number of records to return
            
        Returns:
            list: List of gambling history records
        """
        query = """
            SELECT gh.*, gbt.name as box_name, gbt.price as box_price
            FROM gambling_history gh
            JOIN gambling_box_types gbt ON gh.box_type_id = gbt.id
            WHERE gh.user_id = %s
            ORDER BY gh.gambled_at DESC
            LIMIT %s
        """
        return await self.execute_query(query, (user_id, limit))