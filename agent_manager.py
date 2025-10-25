"""
Agent Manager for coordinating multiple agents.
"""
from typing import List, Dict, Optional
import asyncio
from agent_base import AgentBase
from message import Message
from console import Console


class AgentManager:
    """Manages multiple agents and routes messages between them."""
    
    def __init__(self, console: Console):
        """
        Initialize the agent manager.
        
        Args:
            console: Console instance for display
        """
        self.console = console
        self.agents: Dict[str, AgentBase] = {}
    
    def add_agent(self, agent: AgentBase):
        """
        Add an agent to the manager.
        
        Args:
            agent: Agent instance to add
        """
        self.agents[agent.name] = agent
        self.console.display_system_message(
            f"Agent '{agent.name}' ({agent.model}) has joined the conversation.",
            "green"
        )
    
    def remove_agent(self, agent_name: str):
        """
        Remove an agent from the manager.
        
        Args:
            agent_name: Name of the agent to remove
        """
        if agent_name in self.agents:
            del self.agents[agent_name]
            self.console.display_system_message(
                f"Agent '{agent_name}' has left the conversation.",
                "yellow"
            )
    
    def get_agent(self, agent_name: str) -> Optional[AgentBase]:
        """Get an agent by name."""
        return self.agents.get(agent_name)
    
    def get_all_agents(self) -> List[AgentBase]:
        """Get list of all agents."""
        return list(self.agents.values())
    
    def get_agents_info(self) -> List[Dict]:
        """Get information about all agents for display."""
        return [
            {
                "name": agent.name,
                "model": agent.model,
                "status": "Active" if agent.is_active else "Inactive"
            }
            for agent in self.agents.values()
        ]
    
    async def broadcast_message(self, message: Message):
        """
        Broadcast a message to all relevant agents.
        
        Args:
            message: Message to broadcast
        """
        # Determine which agents should receive this message
        tasks = []
        
        for agent in self.agents.values():
            if agent.should_process_message(message):
                # Create async task for each agent
                tasks.append(self._process_agent_message(agent, message))
          # Process all agents concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_agent_message(self, agent: AgentBase, message: Message):
        """
        Process a message for a specific agent.
        THREAD-SAFE: Uses async display to prevent race conditions.
        
        Args:
            agent: Agent to process the message
            message: Message to process
        """
        try:
            # Agent processes the message and optionally returns a response
            response = await agent.process(message)
            
            # If agent returns a response, display it (THREAD-SAFE)
            if response:
                await self.console.display_message_async(response)
                
                # If response is for other agents, route it
                if response.receivers and "user" not in response.receivers:
                    await self.broadcast_message(response)
                    
        except Exception as e:
            # Error display should also be atomic
            async with self.console._display_lock:
                self.console.display_agent_error(
                    agent.name,
                    f"Error processing message: {str(e)}"
                )
