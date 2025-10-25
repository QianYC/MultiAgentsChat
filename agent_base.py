"""
Agent base class with concurrent streaming support.
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Dict, Optional
from datetime import datetime
from console import Console
from message import Message


class AgentBase(ABC):
    """
    Abstract base class for all agents.
    Supports concurrent streaming without blocking other agents.
    """
    
    def __init__(self, name: str, model: str, console: Console):
        """
        Initialize the agent.
        
        Args:
            name: Display name for the agent
            model: Model identifier
            console: Console instance
        """
        self.name = name
        self.model = model
        self.console = console
        self.conversation_history: List[Dict] = []
        self.is_active = True
    
    @abstractmethod
    async def process(self, message: Message) -> None:
        """
        Process a message and respond.
        Agent should call stream_response() or send_response().
        
        Args:
            message: Incoming message to process
        """
        pass
    
    def should_process_message(self, message: Message) -> bool:
        """
        Check if this agent should process the message.
        
        Args:
            message: Message to check
            
        Returns:
            True if agent should process
        """
        if message.sender == self.name:
            return False
        return message.is_for(self.name)
    
    async def stream_response(self, response_stream: AsyncIterator[str],
                             receivers: Optional[List[str]] = None):
        """
        Stream a response using the message queue.
        Non-blocking - other agents can stream simultaneously.
        
        Args:
            response_stream: Async iterator of response chunks
            receivers: List of receivers or None for user
        """
        # Start a new message in the queue
        message_id = self.console.start_agent_message(self.name, receivers)
        
        full_response = ""
        
        try:
            # Stream chunks
            async for chunk in response_stream:
                full_response += chunk
                # Update the message in queue (non-blocking)
                self.console.update_agent_message(message_id, chunk)
            
            # Mark as complete
            self.console.complete_agent_message(message_id)
            
            # Add to conversation history
            self.add_to_history("assistant", full_response)
            
        except Exception as e:
            # Mark as complete even on error
            self.console.update_agent_message(message_id, f"\n\n[Error: {str(e)}]")
            self.console.complete_agent_message(message_id)
            raise
    
    def send_response(self, content: str, receivers: Optional[List[str]] = None):
        """
        Send a non-streaming response.
        
        Args:
            content: Response content
            receivers: List of receivers or None for user
        """
        message_id = self.console.start_agent_message(self.name, receivers)
        self.console.update_agent_message(message_id, content)
        self.console.complete_agent_message(message_id)
        
        self.add_to_history("assistant", content)
    
    def add_to_history(self, role: str, content: str):
        """Add to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    def get_history(self) -> List[Dict]:
        """Get conversation history."""
        return self.conversation_history
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def get_info(self) -> Dict:
        """Get agent information."""
        return {
            "name": self.name,
            "model": self.model,
            "status": "Active" if self.is_active else "Inactive",
            "message_count": len(self.conversation_history)
        }
    
    def deactivate(self):
        """Deactivate this agent."""
        self.is_active = False
    
    def activate(self):
        """Activate this agent."""
        self.is_active = True
