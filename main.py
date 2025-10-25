"""
Main entry point for the multi-agent LLM chat console application.
Uses concurrent streaming architecture with message queue.
"""
import asyncio
from datetime import datetime
from console import Console
from streaming_demo_agent import StreamingDemoAgent
from message import Message, MessageParser


async def main():
    """Main application loop with concurrent streaming."""
    # Initialize console
    console = Console(refresh_rate=10)
    
    # Display welcome message
    console.display_welcome()
    
    # Initialize agents
    console.display_system_message(
        "Initializing demo agents...",
        "cyan"
    )
    
    # Create demo agents with concurrent streaming support
    agents = []
    agents.append(StreamingDemoAgent(
        "GPT-4", "gpt-4-turbo", console,
        chars_per_second=80, stream_length="medium"
    ))
    agents.append(StreamingDemoAgent(
        "Claude", "claude-3-opus", console,
        chars_per_second=90, stream_length="medium"
    ))
    agents.append(StreamingDemoAgent(
        "Gemini", "gemini-pro", console,
        chars_per_second=70, stream_length="medium"
    ))
    
    console.display_system_message(
        f"✅ {len(agents)} agents ready! Starting display loop...",
        "green"
    )
    console.print("")
    
    # Display agents info
    agents_info = [
        {
            "name": agent.name,
            "model": agent.model,
            "status": "Active"
        }
        for agent in agents
    ]
    console.display_agents_list(agents_info)
    
    # Start the display loop for concurrent streaming
    await console.start_display_loop()
    
    # Main loop
    while True:
        try:            # Get user input (this pauses the display loop temporarily)
            # In production, you'd want to handle this better
            await console.stop_display_loop()
            user_input = console.get_user_input()
            await console.start_display_loop()
            
            # Handle commands
            if user_input.lower() in ['exit', 'quit']:
                await console.stop_display_loop()
                console.display_system_message("Goodbye! 👋", "cyan")
                break
            
            elif user_input.lower() == 'clear':
                await console.stop_display_loop()
                console.clear()
                console.display_welcome()
                await console.start_display_loop()
            
            elif user_input.lower() == 'history':
                await console.stop_display_loop()
                console.display_history()
                input("Press Enter to continue...")
                await console.start_display_loop()
            
            elif user_input.lower() == 'agents':
                await console.stop_display_loop()
                console.display_agents_list(agents_info)
                input("Press Enter to continue...")
                await console.start_display_loop()
            
            # Scrolling commands
            elif user_input.lower() in ['up', 'u']:
                console.scroll_up(1)
                
            elif user_input.lower() in ['down', 'd']:
                console.scroll_down(1)
                
            elif user_input.lower() == 'top':
                console.scroll_to_top()
                
            elif user_input.lower() in ['bottom', 'b']:
                console.scroll_to_bottom()
                
            elif user_input.lower() in ['pageup', 'pu']:
                console.page_up()
                
            elif user_input.lower() in ['pagedown', 'pd']:
                console.page_down()
                
            elif user_input.strip():
                # Parse message to extract receivers and content
                content, receivers = MessageParser.parse(user_input)
                
                # Submit user message to queue
                console.submit_user_message(content, receivers)
                
                # Create message object for agents
                user_message = Message(
                    sender="user",
                    content=content,
                    timestamp=datetime.now(),
                    receivers=receivers,
                    sender_type="user"
                )
                  # Broadcast to agents (they will process concurrently)
                tasks = []
                for agent in agents:
                    if agent.should_process_message(user_message):
                        tasks.append(agent.process(user_message))
                
                # Wait for all agents to complete
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Force one final display refresh to show all completed messages
                    # This ensures the last agent's output is fully displayed
                    await console.force_display_refresh()
                
        except KeyboardInterrupt:
            await console.stop_display_loop()
            console.print("\n")
            console.display_system_message("Interrupted by user. Exiting...", "yellow")
            break
        except Exception as e:
            await console.stop_display_loop()
            console.display_system_message(f"Error: {str(e)}", "red")
            import traceback
            traceback.print_exc()
            input("Press Enter to continue...")
            await console.start_display_loop()


if __name__ == "__main__":
    asyncio.run(main())
