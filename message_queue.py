"""
Thread-safe message queue with support for concurrent streaming.
Allows multiple agents to stream simultaneously without blocking.

Uses array-based indexing with lock-free updates.
"""
import asyncio
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from message import Message


@dataclass
class StreamingMessage:
    """
    Represents a message that may be in the process of streaming.
    """
    message_id: str
    sender: str
    content: str
    timestamp: datetime
    receivers: Optional[List[str]]
    sender_type: str
    is_complete: bool = False
    last_update: datetime = field(default_factory=datetime.now)
    
    def update_content(self, new_chunk: str):
        """Append new content chunk."""
        self.content += new_chunk
        self.last_update = datetime.now()
    
    def mark_complete(self):
        """Mark this message as complete."""
        self.is_complete = True
        self.last_update = datetime.now()
    
    def to_message(self) -> Message:
        """Convert to regular Message object."""
        return Message(
            sender=self.sender,
            content=self.content,
            timestamp=self.timestamp,
            receivers=self.receivers,
            sender_type=self.sender_type
        )


class MessageQueue:
    """
    Thread-safe message queue that supports:
    1. Concurrent message submission from multiple agents
    2. Lock-free updates for streaming messages (uses array indexing)
    3. Fixed-rate display refresh
    
    Design: Lock only needed for queue modifications (submit/cleanup).
    Updates are lock-free using stable array indices.
    
    Key insight: Array indices remain stable during normal operation.
    - submit_message() appends to end (doesn't change existing indices)
    - update_message() uses index to access array (lock-free)
    - cleanup_old_messages() is rare and uses lock
    """
    
    def __init__(self):
        self._queue: List[StreamingMessage] = []
        self._lock = Lock()  # Only for queue structure modifications
        self._next_id = 0
    
    def submit_message(self, sender: str, initial_content: str, 
                      receivers: Optional[List[str]] = None,
                      sender_type: str = "agent") -> int:
        """
        Submit a new message to the queue.
        Returns INDEX for future updates.
        Thread-safe using lock.
        
        Args:
            sender: Name of sender
            initial_content: Initial content (may be empty for streaming)
            receivers: List of receivers or None for broadcast
            sender_type: "user" or "agent"
            
        Returns:
            Index in queue for updating this message
        """
        with self._lock:
            message_id = f"{sender}_{self._next_id}"
            self._next_id += 1
            
            streaming_msg = StreamingMessage(
                message_id=message_id,
                sender=sender,
                content=initial_content,
                timestamp=datetime.now(),
                receivers=receivers,
                sender_type=sender_type,
                is_complete=False
            )
            
            # Add to queue and return index
            idx = len(self._queue)
            self._queue.append(streaming_msg)
            
            return idx  # Return array index directly
    
    def update_message(self, idx: int, new_chunk: str) -> bool:
        """
        Append new content to an existing streaming message.
        LOCK-FREE for performance during streaming.
        
        Safe because:
        - Array indices are stable (no inserts/deletes during streaming)
        - Partial updates acceptable during streaming
        - Once complete, no more updates
        
        Args:
            idx: Index returned from submit_message
            new_chunk: Content chunk to append
            
        Returns:
            True if update successful, False if index out of bounds
        """
        # No lock needed - direct array access with index
        if idx < 0 or idx >= len(self._queue):
            return False
        
        # Lock-free update - acceptable to race with display
        self._queue[idx].update_content(new_chunk)
        return True
    
    def complete_message(self, idx: int) -> bool:
        """
        Mark a message as complete (no more streaming).
        LOCK-FREE for performance.
        
        Args:
            idx: Index of message to complete
            
        Returns:
            True if successful
        """
        # No lock needed - direct array access
        if idx < 0 or idx >= len(self._queue):
            return False
        
        # Lock-free completion
        self._queue[idx].mark_complete()
        return True
    
    def get_display_snapshot(self) -> List[StreamingMessage]:
        """
        Get a snapshot of all messages for display.
        Thread-safe using lock.
        Creates a copy to avoid holding lock during display.
        
        Returns:
            List of StreamingMessage objects (copy)
        """
        with self._lock:
            # Return a shallow copy of the queue
            return self._queue.copy()
    
    def cleanup_old_messages(self, keep_last_n: int = 100):
        """
        Remove old completed messages to prevent memory growth.
        Keeps last N messages.
        Thread-safe using lock.
        
        ⚠️  WARNING: This invalidates old indices!
        Only call this when no active streaming is happening.
        
        Args:
            keep_last_n: Number of recent messages to keep
        """
        with self._lock:
            if len(self._queue) <= keep_last_n:
                return
            
            # Keep only recent messages
            self._queue = self._queue[-keep_last_n:]
    
    def clear(self):
        """Clear all messages. Thread-safe."""
        with self._lock:
            self._queue.clear()
    
    def get_queue_size(self) -> int:
        """Get current queue size. Thread-safe."""
        with self._lock:
            return len(self._queue)
    
    def get_streaming_count(self) -> int:
        """Get count of messages currently streaming. Thread-safe."""
        with self._lock:
            return sum(1 for msg in self._queue if not msg.is_complete)
    
    def get_completed_messages(self, last_n: Optional[int] = None) -> List[Message]:
        """
        Get completed messages as Message objects (for history display).
        Thread-safe using lock.
        
        This method filters for complete messages and converts them to
        simplified Message objects (without streaming metadata).
        
        Args:
            last_n: Optional limit to last N messages. If None, returns all.
        
        Returns:
            List of Message objects (only completed messages)
        """
        with self._lock:
            # Filter for complete messages only
            completed = [msg for msg in self._queue if msg.is_complete]
            
            # Apply limit if specified
            if last_n is not None and len(completed) > last_n:
                completed = completed[-last_n:]
            
            # Convert to Message objects
            return [msg.to_message() for msg in completed]
