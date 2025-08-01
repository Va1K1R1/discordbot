from datetime import datetime
from config.database import DatabaseManager
from database.models import BaseModel

class BettingModel(BaseModel):
    """
    Model for managing betting events and user bets.
    """
    
    async def create_betting_event(self, guild_id: int, creator_id: int, title: str, description: str = None):
        """
        Create a new betting event.
        
        Args:
            guild_id (int): The guild ID
            creator_id (int): The creator's ID
            title (str): The event title
            description (str, optional): Event description
            
        Returns:
            int or None: The event ID if successful, None otherwise
        """
        try:
            query = """
                INSERT INTO betting_events 
                (guild_id, creator_id, title, description) 
                VALUES (%s, %s, %s, %s)
            """
            result = await self.execute_query(
                query, 
                (guild_id, creator_id, title, description),
                fetch=True
            )
            
            return result['lastrowid'] if result and 'lastrowid' in result else None
            
        except Exception as e:
            print(f"Error creating betting event: {e}")
            return None
            
    async def add_betting_option(self, event_id: int, name: str, description: str = None, odds: float = 1.0):
        """
        Add an option to a betting event.
        
        Args:
            event_id (int): The event ID
            name (str): The option name
            description (str, optional): Option description
            odds (float, optional): The odds for this option
            
        Returns:
            int or None: The option ID if successful, None otherwise
        """
        try:
            query = """
                INSERT INTO betting_options 
                (event_id, name, description, odds) 
                VALUES (%s, %s, %s, %s)
            """
            result = await self.execute_query(
                query, 
                (event_id, name, description, odds),
                fetch=True
            )
            
            return result['lastrowid'] if result and 'lastrowid' in result else None
            
        except Exception as e:
            print(f"Error adding betting option: {e}")
            return None
            
    async def get_betting_event(self, event_id: int):
        """
        Get a specific betting event.
        
        Args:
            event_id (int): The event ID
            
        Returns:
            dict or None: The event information, or None if not found
        """
        query = "SELECT * FROM betting_events WHERE id = %s"
        results = await self.execute_query(query, (event_id,))
        return results[0] if results else None
        
    async def get_active_betting_events(self, guild_id: int):
        """
        Get all active betting events for a guild.
        
        Args:
            guild_id (int): The guild ID
            
        Returns:
            list: List of active betting events
        """
        query = """
            SELECT * FROM betting_events 
            WHERE guild_id = %s AND status = 'OPEN'
            ORDER BY created_at DESC
        """
        return await self.execute_query(query, (guild_id,))
        
    async def get_betting_options(self, event_id: int):
        """
        Get all options for a betting event.
        
        Args:
            event_id (int): The event ID
            
        Returns:
            list: List of betting options
        """
        query = "SELECT * FROM betting_options WHERE event_id = %s"
        return await self.execute_query(query, (event_id,))
        
    async def get_betting_option(self, option_id: int):
        """
        Get a specific betting option.
        
        Args:
            option_id (int): The option ID
            
        Returns:
            dict or None: The option information, or None if not found
        """
        query = "SELECT * FROM betting_options WHERE id = %s"
        results = await self.execute_query(query, (option_id,))
        return results[0] if results else None
        
    async def lock_betting_event(self, event_id: int):
        """
        Lock a betting event so no more bets can be placed.
        
        Args:
            event_id (int): The event ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = """
                UPDATE betting_events 
                SET status = 'LOCKED', locked_at = CURRENT_TIMESTAMP
                WHERE id = %s AND status = 'OPEN'
            """
            await self.execute_query(query, (event_id,), fetch=False)
            return True
        except Exception as e:
            print(f"Error locking betting event: {e}")
            return False
            
    async def settle_betting_event(self, event_id: int, winning_option_id: int):
        """
        Settle a betting event by declaring a winning option.
        
        Args:
            event_id (int): The event ID
            winning_option_id (int): The winning option ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update event status
            query = """
                UPDATE betting_events 
                SET status = 'SETTLED', settled_at = CURRENT_TIMESTAMP, winning_option_id = %s
                WHERE id = %s AND (status = 'OPEN' OR status = 'LOCKED')
            """
            await self.execute_query(query, (winning_option_id, event_id), fetch=False)
            
            # Update bets status
            query = """
                UPDATE user_bets 
                SET status = CASE 
                    WHEN option_id = %s THEN 'WON' 
                    ELSE 'LOST' 
                END,
                settled_at = CURRENT_TIMESTAMP
                WHERE event_id = %s AND status = 'ACTIVE'
            """
            await self.execute_query(query, (winning_option_id, event_id), fetch=False)
            
            return True
        except Exception as e:
            print(f"Error settling betting event: {e}")
            return False
            
    async def cancel_betting_event(self, event_id: int):
        """
        Cancel a betting event and refund all bets.
        
        Args:
            event_id (int): The event ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update event status
            query = """
                UPDATE betting_events 
                SET status = 'CANCELLED', settled_at = CURRENT_TIMESTAMP
                WHERE id = %s AND (status = 'OPEN' OR status = 'LOCKED')
            """
            await self.execute_query(query, (event_id,), fetch=False)
            
            # Update bets status
            query = """
                UPDATE user_bets 
                SET status = 'REFUNDED', settled_at = CURRENT_TIMESTAMP
                WHERE event_id = %s AND status = 'ACTIVE'
            """
            await self.execute_query(query, (event_id,), fetch=False)
            
            return True
        except Exception as e:
            print(f"Error cancelling betting event: {e}")
            return False
            
    async def place_bet(self, user_id: int, event_id: int, option_id: int, amount: int):
        """
        Place a bet on a betting option.
        
        Args:
            user_id (int): The user's ID
            event_id (int): The event ID
            option_id (int): The option ID
            amount (int): The bet amount in points
            
        Returns:
            tuple: (success, message, bet_id)
        """
        try:
            # Check if the event is open for betting
            event = await self.get_betting_event(event_id)
            if not event or event['status'] != 'OPEN':
                return False, "이 이벤트는 더 이상 베팅을 받지 않습니다.", None
                
            # Get the option to calculate potential winnings
            option = await self.get_betting_option(option_id)
            if not option or option['event_id'] != event_id:
                return False, "유효하지 않은 베팅 옵션입니다.", None
                
            # Calculate potential winnings
            potential_winnings = int(amount * option['odds'])
            
            # Insert the bet
            query = """
                INSERT INTO user_bets 
                (user_id, event_id, option_id, amount, potential_winnings) 
                VALUES (%s, %s, %s, %s, %s)
            """
            result = await self.execute_query(
                query, 
                (user_id, event_id, option_id, amount, potential_winnings),
                fetch=True
            )
            
            bet_id = result['lastrowid'] if result and 'lastrowid' in result else None
            
            return True, f"{amount:,} 포인트를 베팅했습니다. 성공 시 {potential_winnings:,} 포인트를 받습니다.", bet_id
            
        except Exception as e:
            print(f"Error placing bet: {e}")
            return False, f"베팅 중 오류가 발생했습니다: {e}", None
            
    async def get_user_bets(self, user_id: int, status: str = None, limit: int = 10):
        """
        Get a user's bets.
        
        Args:
            user_id (int): The user's ID
            status (str, optional): Filter by bet status
            limit (int, optional): The maximum number of records to return
            
        Returns:
            list: List of user bets
        """
        if status:
            query = """
                SELECT ub.*, be.title as event_title, bo.name as option_name, bo.odds
                FROM user_bets ub
                JOIN betting_events be ON ub.event_id = be.id
                JOIN betting_options bo ON ub.option_id = bo.id
                WHERE ub.user_id = %s AND ub.status = %s
                ORDER BY ub.placed_at DESC
                LIMIT %s
            """
            return await self.execute_query(query, (user_id, status, limit))
        else:
            query = """
                SELECT ub.*, be.title as event_title, bo.name as option_name, bo.odds
                FROM user_bets ub
                JOIN betting_events be ON ub.event_id = be.id
                JOIN betting_options bo ON ub.option_id = bo.id
                WHERE ub.user_id = %s
                ORDER BY ub.placed_at DESC
                LIMIT %s
            """
            return await self.execute_query(query, (user_id, limit))
            
    async def get_event_bets(self, event_id: int):
        """
        Get all bets for a betting event.
        
        Args:
            event_id (int): The event ID
            
        Returns:
            list: List of bets for the event
        """
        query = """
            SELECT ub.*, u.username
            FROM user_bets ub
            JOIN user_points u ON ub.user_id = u.user_id
            WHERE ub.event_id = %s
            ORDER BY ub.placed_at DESC
        """
        return await self.execute_query(query, (event_id,))
        
    async def get_winning_bets(self, event_id: int, winning_option_id: int):
        """
        Get all winning bets for a betting event.
        
        Args:
            event_id (int): The event ID
            winning_option_id (int): The winning option ID
            
        Returns:
            list: List of winning bets
        """
        query = """
            SELECT ub.*, u.username
            FROM user_bets ub
            JOIN user_points u ON ub.user_id = u.user_id
            WHERE ub.event_id = %s AND ub.option_id = %s AND ub.status = 'ACTIVE'
            ORDER BY ub.placed_at DESC
        """
        return await self.execute_query(query, (event_id, winning_option_id))