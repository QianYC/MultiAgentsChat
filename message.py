"""
Message system for bulletin board-style communication.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class Message:
    """Represents a message in the bulletin board system."""
    sender: str  # "user" or agent name
    content: str
    timestamp: datetime
    receivers: Optional[List[str]] = None  # None means broadcast to all
    sender_type: str = "user"  # "user" or "agent"
    
    def is_broadcast(self) -> bool:
        """Check if this is a broadcast message (sent to all)."""
        return self.receivers is None or len(self.receivers) == 0
    
    def is_for(self, recipient: str) -> bool:
        """
        Check if this message is intended for a specific recipient.
        
        Args:
            recipient: Name of the potential recipient
            
        Returns:
            True if message is for this recipient (broadcast or explicitly targeted)
        """
        if self.is_broadcast():
            return True
        return recipient in self.receivers
    
    def get_receiver_display(self) -> str:
        """Get display string for receivers."""
        if self.is_broadcast():
            return "ALL"
        return ", ".join(self.receivers)


class MessageParser:
    """Parse user input to extract receivers and message content."""
    
    @staticmethod
    def parse(input_text: str) -> tuple[str, Optional[List[str]]]:
        """
        Parse input text to extract receivers and content.
        
        Format: @receiver1,receiver2 message content
        or just: message content (broadcast)
        
        Args:
            input_text: Raw input from user/agent
            
        Returns:
            Tuple of (content, receivers_list)
            receivers_list is None for broadcast
        """
        input_text = input_text.strip()
        
        # Check if message starts with @
        if input_text.startswith('@'):
            # Find the first space to separate receivers from content
            space_idx = input_text.find(' ')
            
            if space_idx == -1:
                # No space found, treat entire input as broadcast
                return input_text, None
            
            # Extract receiver string and content
            receiver_str = input_text[1:space_idx]  # Remove @ and get receivers
            content = input_text[space_idx + 1:].strip()
            
            if not content:
                # No content, treat as broadcast
                return input_text, None
            
            # Parse receivers (comma-separated)
            receivers = [r.strip() for r in receiver_str.split(',') if r.strip()]
            
            if not receivers:
                # No valid receivers, treat as broadcast
                return input_text, None
            
            return content, receivers
        
        # No @ prefix, broadcast message
        return input_text, None
