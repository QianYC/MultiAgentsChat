"""
Enhanced Console with concurrent streaming support.
Uses message queue for simultaneous agent streaming.
"""
from typing import Dict, List, Optional
from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from datetime import datetime
import asyncio
from message import Message
from message_queue import MessageQueue, StreamingMessage


class Console:
    """
    Enhanced console with concurrent streaming support.
    
    Key improvements:
    1. Multiple agents can stream simultaneously
    2. Message queue with fixed-rate display refresh (10 FPS default)    3. No blocking - agents submit updates asynchronously
    4. Clean, organized display even with concurrent streams
    """
    
    def __init__(self, refresh_rate: int = 10, window_size: int = 10):
        """
        Initialize console.
        
        Args:
            refresh_rate: Display refresh rate (updates per second)
            window_size: Number of messages to display in the sliding window
        """
        self.rich_console = RichConsole()
        self.message_queue = MessageQueue()
        self.refresh_rate = refresh_rate
        self.window_size = window_size
        self._display_task: Optional[asyncio.Task] = None
        self._is_displaying = False
        
        # Sliding window state
        self._window_offset = 0  # Offset from the end of queue
        self._auto_scroll = True  # Auto-scroll to latest messages
        self._total_messages = 0  # Track total messages for scroll bounds
    
    def display_welcome(self):
        """Display welcome banner."""
        welcome_text = """
# 🤖 Multi-Agent LLM Chat Console (Concurrent Streaming)

Welcome! This console supports **concurrent streaming** from multiple agents!

**Key Features:**
- ✨ Multiple agents can stream simultaneously
- ⚡ No blocking - all agents respond in parallel
- 🎯 Fixed-rate display refresh (smooth updates)
- 📊 Message queue with thread-safe operations

**Message Routing:**
- Type `message` to broadcast to ALL agents
- Type `@agent1,agent2 message` to send to specific agents

**Commands:**
- `exit` or `quit` - Exit
- `clear` - Clear screen
- `history` - View history
- `agents` - List agents

**Scrolling:**
- Type `up` or `u` - Scroll up 1 message (older messages)
- Type `down` or `d` - Scroll down 1 message (newer messages)
- Type `pageup` or `pu` - Scroll up one page (window size)
- Type `pagedown` or `pd` - Scroll down one page (window size)
- Type `top` - Jump to oldest messages
- Type `bottom` or `b` - Jump to newest messages (auto-scroll)

**How it works:**
1. Agents submit messages to queue (non-blocking)
2. Agents stream chunks to their messages (parallel)
3. Console displays all messages at fixed rate (smooth)
        """
        self.rich_console.print(Panel(
            Markdown(welcome_text),
            title="[bold cyan]Welcome to Concurrent Streaming Console[/bold cyan]",
            border_style="cyan"
        ))
        self.rich_console.print()
    
    async def start_display_loop(self):
        """
        Start the display loop that refreshes at fixed rate.
        This allows concurrent streaming updates.
        """
        if self._is_displaying:
            return
        
        self._is_displaying = True
        self._display_task = asyncio.create_task(self._display_loop())
    
    async def stop_display_loop(self):
        """Stop the display loop."""
        self._is_displaying = False
        if self._display_task:
            await self._display_task
            self._display_task = None
    
    async def force_display_refresh(self):
        """
        Force an immediate display refresh outside the normal loop.
        
        This is useful for ensuring the final state is shown after
        all streaming completes. Since the display loop runs at a fixed
        rate, there's a race condition where agents complete but the
        loop doesn't get one final refresh before stopping.
        
        This method displays the current state immediately without
        using the Live context.
        """
        messages = self.message_queue.get_display_snapshot()
        if messages:
            layout = self._build_display(messages)
            self.rich_console.print(layout)
    
    async def _display_loop(self):
        """
        Main display loop - refreshes display at fixed rate.
        Shows all messages in queue, updating streaming ones.
        """
        refresh_interval = 1.0 / self.refresh_rate
        
        with Live(console=self.rich_console, refresh_per_second=self.refresh_rate, 
                  vertical_overflow="visible") as live:
            while self._is_displaying:
                # Get snapshot of all messages
                messages = self.message_queue.get_display_snapshot()
                
                if messages:
                    # Build display layout
                    layout = self._build_display(messages)
                    live.update(layout)
                  # Wait for next refresh
                await asyncio.sleep(refresh_interval)
    
    def _build_display(self, messages: List[StreamingMessage]) -> Layout:
        """
        Build rich layout showing messages using sliding window algorithm.
        
        The sliding window allows viewing a subset of messages:
        - window_size: number of messages to show
        - window_offset: offset from the end (0 = latest messages)
        
        Args:
            messages: List of all messages to display from
            
        Returns:
            Rich Layout object
        """
        layout = Layout()
        self._total_messages = len(messages)
        
        if not messages:
            layout.update(Panel(
                "[dim]No messages yet. Type a message to get started![/dim]",
                border_style="dim"
            ))
            return layout
        
        # Calculate sliding window bounds
        total = len(messages)
        
        # If auto-scroll is enabled, always show latest messages
        if self._auto_scroll:
            self._window_offset = 0
        
        # Calculate window start and end indices
        # window_offset=0 means show the last N messages
        # window_offset=5 means show messages ending 5 from the end
        end_idx = total - self._window_offset
        start_idx = max(0, end_idx - self.window_size)
        
        # Clamp to valid range
        end_idx = max(self.window_size, end_idx)
        start_idx = max(0, start_idx)
        
        # Extract window
        window_messages = messages[start_idx:end_idx]
        
        panels = []
        for msg in window_messages:
            # Determine style
            if msg.sender_type == "user":
                title_color = "green"
                border_color = "green"
                icon = "👤"
            else:
                title_color = "blue"
                border_color = "blue"
                icon = "🤖"
            
            # Build title
            receiver_display = "ALL" if not msg.receivers else ", ".join(msg.receivers)
            title = f"[bold {title_color}]{icon} {msg.sender}[/bold {title_color}]"
            title += f" [dim]→[/dim] [yellow]{receiver_display}[/yellow]"
            title += f" [dim]({msg.timestamp.strftime('%H:%M:%S')})[/dim]"
            
            # Add streaming indicator
            if not msg.is_complete:
                title += " [blink yellow]●[/blink yellow]"  # Blinking dot for streaming
              # Create panel
            content = msg.content if msg.content else "[dim]waiting...[/dim]"
            panel = Panel(
                Markdown(content) if len(content) > 50 else f"[white]{content}[/white]",
                title=title,
                border_style=border_color,
                padding=(0, 2)
            )
            panels.append(panel)
        
        # Show queue stats with scroll position
        stats = Text()
        stats.append(f"Queue: {self.message_queue.get_queue_size()} messages  ", style="dim")
        stats.append(f"Streaming: {self.message_queue.get_streaming_count()}  ", 
                    style="yellow bold")
        
        # Show scroll position
        if total > self.window_size:
            scroll_info = f"Viewing: {start_idx+1}-{end_idx} of {total}  "
            if self._auto_scroll:
                scroll_info += "[AUTO-SCROLL ON]"
            else:
                scroll_info += f"[SCROLL: offset={self._window_offset}]"
            stats.append(scroll_info, style="cyan")
        
        panels.insert(0, Panel(stats, border_style="dim"))
        
        # Combine all panels
        from rich.console import Group
        layout.update(Group(*panels))
        
        return layout
    
    # Sliding window control methods
    
    def scroll_up(self, amount: int = 1):
        """
        Scroll up (towards older messages).
        
        Args:
            amount: Number of messages to scroll
        """
        self._auto_scroll = False
        max_offset = max(0, self._total_messages - self.window_size)
        self._window_offset = min(self._window_offset + amount, max_offset)
    
    def scroll_down(self, amount: int = 1):
        """
        Scroll down (towards newer messages).
        
        Args:
            amount: Number of messages to scroll
        """
        self._window_offset = max(0, self._window_offset - amount)
        
        # Re-enable auto-scroll if we're at the bottom
        if self._window_offset == 0:
            self._auto_scroll = True
    
    def scroll_to_top(self):
        """Jump to the oldest messages."""
        self._auto_scroll = False
        self._window_offset = max(0, self._total_messages - self.window_size)
    
    def scroll_to_bottom(self):
        """Jump to the newest messages and enable auto-scroll."""
        self._window_offset = 0
        self._auto_scroll = True
    
    def page_up(self):
        """Scroll up by one window size."""
        self.scroll_up(self.window_size)
    
    def page_down(self):
        """Scroll down by one window size."""
        self.scroll_down(self.window_size)
    
    def submit_user_message(self, content: str, receivers: Optional[List[str]] = None) -> str:
        """
        Submit a user message (non-streaming).
        
        Args:
            content: Message content
            receivers: List of receivers or None for broadcast
            
        Returns:
            message_id
        """
        message_id = self.message_queue.submit_message(
            sender="user",
            initial_content=content,
            receivers=receivers,
            sender_type="user"
        )
        # User messages are immediately complete
        self.message_queue.complete_message(message_id)
        
        return message_id
    
    def start_agent_message(self, agent_name: str,
                           receivers: Optional[List[str]] = None) -> int:
        """
        Start a new streaming message from an agent.
        Agent will update this message with chunks.
        
        Args:
            agent_name: Name of the agent
            receivers: List of receivers or None for user
            
        Returns:
            Index for updating this message
        """
        if receivers is None:
            receivers = ["user"]
        
        return self.message_queue.submit_message(
            sender=agent_name,
            initial_content="",  # Start empty
            receivers=receivers,
            sender_type="agent"
        )
    
    def update_agent_message(self, idx: int, chunk: str) -> bool:
        """
        Append a chunk to an agent's streaming message.
        
        Args:
            idx: Index returned from start_agent_message
            chunk: Content chunk to append
            
        Returns:
            True if successful
        """
        return self.message_queue.update_message(idx, chunk)
    def complete_agent_message(self, idx: int) -> bool:
        """
        Mark an agent message as complete.
        
        Args:
            idx: Index of the message
            
        Returns:
            True if successful
        """
        return self.message_queue.complete_message(idx)
    
    def display_system_message(self, message: str, style: str = "yellow"):
        """Display a system message (non-streaming)."""
        self.rich_console.print(
            Panel(
                f"[{style}]{message}[/{style}]",
                title=f"[bold {style}]System[/bold {style}]",
                border_style=style,
                padding=(0, 2)
            )
        )
        self.rich_console.print()
    
    def display_agents_list(self, agents: List[Dict]):
        """Display list of agents."""
        table = Table(title="Active Agents", show_header=True, header_style="bold cyan")
        table.add_column("Agent Name", style="blue")
        table.add_column("Model", style="green")
        table.add_column("Status", style="yellow")
        
        for agent in agents:
            table.add_row(
                agent.get("name", "Unknown"),
                agent.get("model", "N/A"),
                agent.get("status", "Active")
            )
        
        self.rich_console.print(table)
        self.rich_console.print()
    def display_history(self):
        """
        Display conversation history.
        
        Retrieves completed messages from the message queue.
        Shows the last 20 messages only.
        """        # Get completed messages from queue (last 20)
        history = self.message_queue.get_completed_messages(last_n=20)
        
        if not history:
            self.display_system_message("No conversation history yet.", "yellow")
            return
        
        self.rich_console.print(Panel(
            "[bold cyan]Conversation History[/bold cyan]",
            border_style="cyan"
        ))
        
        for msg in history:
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            receiver_display = msg.get_receiver_display()
            
            icon = "👤" if msg.sender_type == "user" else "🤖"
            color = "green" if msg.sender_type == "user" else "blue"
            
            self.rich_console.print(
                f"[{color}]{icon} {msg.sender} → {receiver_display} ({timestamp}):[/{color}]"
            )
              # Display full message content with proper wrapping
            # Use Panel for better visual separation and automatic text wrapping
            content_text = Text(msg.content)
            content_panel = Panel(
                content_text,
                border_style="dim",
                padding=(0, 1),
                expand=False            )
            self.rich_console.print(content_panel)
            self.rich_console.print()
    
    def clear(self):
        """Clear the console."""
        self.rich_console.clear()
        self.message_queue.clear()
    
    def get_user_input(self, prompt: str = "You") -> str:
        """Get input from user."""
        return input(f"\033[1;32m{prompt}\033[0m > ")
    
    def print(self, message: str, style: str = ""):
        """Simple print."""
        if style:
            self.rich_console.print(f"[{style}]{message}[/{style}]")
        else:
            self.rich_console.print(message)
