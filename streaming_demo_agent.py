"""
Streaming demo agent - demonstrates concurrent streaming.
"""
import asyncio
from typing import Optional, AsyncIterator
from agent_base import AgentBase
from message import Message
from console import Console


class StreamingDemoAgent(AgentBase):
    """
    Demo agent that streams responses character by character.
    Multiple instances can stream concurrently without blocking!
    """
    
    def __init__(self, name: str, model: str, console: Console,
                 chars_per_second: int = 50, stream_length: str = "medium"):
        """
        Initialize streaming demo agent.
        
        Args:
            name: Agent name
            model: Model identifier
            console: Console instance
            chars_per_second: Streaming speed
            stream_length: "short", "medium", or "long"
        """
        super().__init__(name, model, console)
        self.chars_per_second = chars_per_second
        self.stream_length = stream_length
    
    async def process(self, message: Message) -> None:
        """Process message and stream response."""
        # Add to history
        self.add_to_history("user", message.content)
        
        # Generate response based on length setting
        response_text = self._generate_response(message)
        
        # Stream the response
        await self.stream_response(
            self._stream_text(response_text),
            receivers=["user"]
        )
    
    async def _stream_text(self, text: str) -> AsyncIterator[str]:
        """
        Stream text character by character.
        
        Args:
            text: Full text to stream
            
        Yields:
            Character chunks
        """
        delay = 1.0 / self.chars_per_second
        chunk_size = max(1, self.chars_per_second // 20)  # 20 updates/sec
        
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            yield chunk
            await asyncio.sleep(delay * len(chunk))
    
    def _generate_response(self, message: Message) -> str:
        """Generate response based on stream length setting."""
        content = message.content.lower()
        
        if self.stream_length == "short":
            return self._short_response(content)
        elif self.stream_length == "long":
            return self._long_response(content)
        else:
            return self._medium_response(content)
    
    def _short_response(self, content: str) -> str:
        """Generate a short response (~50 chars)."""
        return f"**{self.name}**: Quick response to your query! ✨"
    
    def _medium_response(self, content: str) -> str:
        """Generate a medium response (~200 chars)."""
        if "hello" in content or "hi" in content:
            return f"""Hello from **{self.name}**! 👋

I'm streaming this response character by character. Notice how I can stream concurrently with other agents without blocking them!"""
        
        elif "concurrent" in content or "parallel" in content:
            return f"""**{self.name} here!**

Yes, this console supports truly concurrent streaming! Multiple agents can stream simultaneously without waiting for each other. Much better UX! ⚡"""
        
        else:
            return f"""**{self.name}** ({self.model}):

This is a demo response showing concurrent streaming. The queue-based architecture allows multiple agents to update their messages in parallel! 🎯"""
    
    def _long_response(self, content: str) -> str:
        """Generate a long response (~500+ chars)."""
        return f"""**{self.name}** - Extended Response 📝

Thank you for your question! I'm demonstrating a **long streaming response** to show how the concurrent streaming architecture handles extended outputs.

**Key Benefits of Queue-Based Streaming:**

1. **No Blocking**: I can stream this long response while other agents stream theirs
2. **Better UX**: Users see all agents responding simultaneously
3. **Scalable**: System supports many concurrent streams
4. **Fair**: No agent monopolizes the display

**Technical Details:**

The message queue uses Compare-and-Swap (CAS) mechanisms with locks to ensure thread-safety. Each agent:
- Submits a message to the queue
- Updates it with chunks as they arrive
- Marks it complete when done

The console refreshes at a fixed rate (e.g., 10 FPS) and displays all messages, creating a smooth streaming experience even with multiple concurrent streams.

**Conclusion:**

This architecture solves the bottleneck problem of sequential streaming. Now all agents can truly work in parallel! 🚀

- {self.name} ({self.model})"""
