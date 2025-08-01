import discord
from datetime import datetime, timedelta
import re
import json

class InputValidator:
    """
    Utility class for validating and sanitizing user input.
    """
    
    @staticmethod
    def sanitize_message_content(content: str) -> str:
        """
        Sanitize message content to prevent injection attacks.
        
        Args:
            content (str): The message content to sanitize
            
        Returns:
            str: The sanitized message content
        """
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Escape special characters
        content = content.replace('`', '\\`').replace('*', '\\*')
        
        # Limit length
        if len(content) > 2000:
            content = content[:1997] + "..."
            
        return content
    
    @staticmethod
    def validate_amount(amount: int, min_val: int = 1, max_val: int = 1000000) -> bool:
        """
        Validate that an amount is within the specified range.
        
        Args:
            amount (int): The amount to validate
            min_val (int): The minimum allowed value
            max_val (int): The maximum allowed value
            
        Returns:
            bool: True if the amount is valid, False otherwise
        """
        return min_val <= amount <= max_val
    
    @staticmethod
    def validate_time_format(time_str: str):
        """
        Validate and parse a time string into a datetime object.
        Supports multiple formats.
        
        Args:
            time_str (str): The time string to validate
            
        Returns:
            datetime or None: The parsed datetime object, or None if invalid
        """
        formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d %H:%M"]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
                
        return None

class MessageFormatter:
    """
    Utility class for formatting messages and embeds.
    """
    
    @staticmethod
    def create_embed(title, description=None, color=discord.Color.blue(), fields=None, footer=None, thumbnail=None):
        """
        Create a Discord embed with the specified parameters.
        
        Args:
            title (str): The embed title
            description (str, optional): The embed description
            color (discord.Color, optional): The embed color
            fields (list, optional): List of field dictionaries with name, value, and inline keys
            footer (str, optional): The embed footer text
            thumbnail (str, optional): URL of the thumbnail image
            
        Returns:
            discord.Embed: The created embed
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now()
        )
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field['name'],
                    value=field['value'],
                    inline=field.get('inline', False)
                )
                
        if footer:
            embed.set_footer(text=footer)
            
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
            
        return embed
    
    @staticmethod
    def format_time_difference(time_delta):
        """
        Format a timedelta into a human-readable string.
        
        Args:
            time_delta (timedelta): The time difference
            
        Returns:
            str: A human-readable string representing the time difference
        """
        days = time_delta.days
        hours, remainder = divmod(time_delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}일")
        if hours > 0:
            parts.append(f"{hours}시간")
        if minutes > 0:
            parts.append(f"{minutes}분")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}초")
            
        return " ".join(parts)

class JsonHandler:
    """
    Utility class for handling JSON data.
    """
    
    @staticmethod
    def load_json(file_path):
        """
        Load JSON data from a file.
        
        Args:
            file_path (str): Path to the JSON file
            
        Returns:
            dict: The loaded JSON data
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading JSON from {file_path}: {e}")
            return {}
    
    @staticmethod
    def save_json(file_path, data):
        """
        Save data to a JSON file.
        
        Args:
            file_path (str): Path to the JSON file
            data: The data to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Error saving JSON to {file_path}: {e}")
            return False