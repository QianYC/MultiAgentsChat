"""
Main entry point for the multi-agent LLM chat console application.
Uses concurrent streaming architecture with message queue.
"""
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from console import Console
from streaming_demo_agent import StreamingDemoAgent
from langgraph_agent import LangGraphAgent
from message import Message, MessageParser

# Load environment variables from .env file
load_dotenv()


async def main():
    """Main application loop with concurrent streaming."""
    # Initialize console
    console = Console(refresh_rate=10)
    
    # Display welcome message
    console.display_welcome()
    
    # Initialize agents
    console.display_system_message(
        "Initializing agents...",
        "cyan"
    )
    
    agents = []
    
    # Check if GitHub Token is available
    has_github = os.getenv("GITHUB_TOKEN") and os.getenv("GITHUB_TOKEN") != "your_github_token_here"
    
    # Create 7 agents using GitHub Copilot
    if has_github:
        agent_configs = [
            ("Alice", "A helpful assistant focused on analysis", "gpt-4"),
            ("Bob", "A creative problem solver", "gpt-4"),
            ("Charlie", "A technical expert", "gpt-4"),
            ("Diana", "A detail-oriented researcher", "gpt-3.5-turbo"),
            ("Eve", "A strategic thinker", "gpt-3.5-turbo"),
            ("Frank", "A logical reasoner", "gpt-3.5-turbo"),
            ("Grace", "A comprehensive advisor", "gpt-4")
        ]
        
        for agent_name, description, model in agent_configs:
            try:
                agents.append(LangGraphAgent(
                    name=agent_name,
                    model=model,
                    console=console,
                    provider="github-copilot",
                    tools=["calculator", "datetime", "search"],
                    show_thinking=True,
                    temperature=0.7
                ))
                console.display_system_message(f"✅ {agent_name} ({description}) initialized", "green")
            except Exception as e:
                console.display_system_message(f"⚠️  Failed to initialize {agent_name}: {str(e)}", "yellow")
    
    # Fallback to demo agents if no API keys available
    if not agents:
        console.display_system_message(
            "No API keys found. Using demo agents instead.",
            "yellow"
        )
        console.display_system_message(
            "To use real LLM agents, copy .env.example to .env and add your API keys.",
            "cyan"
        )
        
        agents.append(StreamingDemoAgent(
            "Demo-GPT-4", "gpt-4-turbo", console,
            chars_per_second=80, stream_length="medium"
        ))
        agents.append(StreamingDemoAgent(
            "Demo-Claude", "claude-3-opus", console,
            chars_per_second=90, stream_length="medium"
        ))
        agents.append(StreamingDemoAgent(
            "Demo-Gemini", "gemini-pro", console,
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
