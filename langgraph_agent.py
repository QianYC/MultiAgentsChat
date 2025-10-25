"""
LangGraph-based agent with reflection, tool use, and streaming support.
Integrates with the concurrent console architecture.
"""
import asyncio
import json
import os
from typing import Optional, List, Dict, Any, Literal, TypedDict, Annotated
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from agent_base import AgentBase
from message import Message
from console import Console


# ============================================================================
# STATE SCHEMA
# ============================================================================

class AgentState(TypedDict):
    """State for the LangGraph agent workflow."""
    messages: Annotated[List[BaseMessage], add_messages]
    user_input: str
    reflection: str  # Thinking process
    plan: str  # Action plan
    need_tools: bool  # Whether tools are needed
    tool_results: List[str]  # Results from tool execution
    final_response: str
    iteration: int


# ============================================================================
# LLM PROVIDER FACTORY
# ============================================================================

class LLMProvider:
    """Factory for creating LLM instances with streaming support."""
    
    @staticmethod
    def create(provider: str, model: str, streaming: bool = True, temperature: float = 0.7):
        """
        Create an LLM instance based on provider.
        
        Args:
            provider: "openai", "anthropic", "google", or "github-copilot"
            model: Model identifier
            streaming: Enable streaming
            temperature: Temperature for generation
            
        Returns:
            LLM instance
        """
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            return ChatOpenAI(
                model=model,
                streaming=streaming,
                temperature=temperature,
                api_key=api_key
            )
        
        elif provider == "github-copilot":
            # GitHub Copilot uses OpenAI-compatible API
            github_token = os.getenv("GITHUB_TOKEN")
            if not github_token:
                raise ValueError("GITHUB_TOKEN not found in environment")
            return ChatOpenAI(
                model=model,
                streaming=streaming,
                temperature=temperature,
                api_key=github_token,
                base_url="https://api.githubcopilot.com",
                default_headers={
                    "Editor-Version": "vscode/1.95.0",
                    "Editor-Plugin-Version": "copilot-chat/0.22.4",
                    "Copilot-Integration-Id": "vscode-chat"
                }
            )
        
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")
            return ChatAnthropic(
                model=model,
                streaming=streaming,
                temperature=temperature,
                api_key=api_key
            )
        
        elif provider == "google":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment")
            return ChatGoogleGenerativeAI(
                model=model,
                streaming=streaming,
                temperature=temperature,
                google_api_key=api_key,
                convert_system_message_to_human=True  # Better compatibility
            )
        
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'openai', 'anthropic', 'google', or 'github-copilot'")


# ============================================================================
# TOOLS
# ============================================================================

def calculator_tool(expression: str) -> str:
    """
    Calculate mathematical expressions safely.
    
    Args:
        expression: Math expression (e.g., "25 * 37 + 100")
        
    Returns:
        Result as string
    """
    try:
        # Safe eval - only allow basic math operations
        allowed_chars = set("0123456789+-*/().% ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression"
        
        result = eval(expression, {"__builtins__": {}}, {})
        return f"{result}"
    except Exception as e:
        return f"Error: {str(e)}"


def datetime_tool(query: str = "") -> str:
    """
    Get current date and time information.
    
    Args:
        query: Optional query ("date", "time", or empty for both)
        
    Returns:
        Current date/time info
    """
    now = datetime.now()
    
    if "date" in query.lower():
        return now.strftime("%Y-%m-%d")
    elif "time" in query.lower():
        return now.strftime("%H:%M:%S")
    else:
        return now.strftime("%Y-%m-%d %H:%M:%S")


def search_tool(query: str) -> str:
    """
    Mock search tool (placeholder for real search API).
    
    Args:
        query: Search query
        
    Returns:
        Mock search results
    """
    # This is a mock - replace with real search API (e.g., Tavily, SerpAPI)
    mock_results = {
        "python": "Python is a high-level programming language known for its simplicity and readability.",
        "ai": "Artificial Intelligence (AI) refers to computer systems that can perform tasks requiring human intelligence.",
        "langgraph": "LangGraph is a library for building stateful, multi-actor applications with LLMs.",
    }
    
    query_lower = query.lower()
    for key, value in mock_results.items():
        if key in query_lower:
            return value
    
    return f"Mock search results for: {query}"


# Create Tool objects
AVAILABLE_TOOLS = {
    "calculator": Tool(
        name="calculator",
        description="Calculate mathematical expressions. Input should be a valid math expression like '25 * 37 + 100'",
        func=calculator_tool
    ),
    "datetime": Tool(
        name="datetime",
        description="Get current date and time. Input can be 'date', 'time', or empty for both",
        func=datetime_tool
    ),
    "search": Tool(
        name="search",
        description="Search for information. Input should be a search query",
        func=search_tool
    ),
}


# ============================================================================
# PROMPTS
# ============================================================================

REFLECTION_PROMPT = """You are a helpful AI assistant. Analyze the user's query carefully and think through your approach.

Consider:
1. What is the user really asking?
2. What information or tools might you need?
3. What's the best way to provide a helpful response?

User query: {user_input}

Think step-by-step about how to approach this:"""


DECISION_PROMPT = """Based on your reflection, decide if you need to use any tools.

Your thinking:
{reflection}

Available tools:
{tools}

Do you need to use any tools to answer: "{user_input}"?

Respond with ONLY a JSON object (no other text):
{{"need_tools": true/false, "tools_to_use": ["tool1", "tool2"], "reasoning": "brief explanation"}}"""


DIRECT_RESPONSE_PROMPT = """Based on your reflection, provide a helpful response.

Your thinking:
{reflection}

User query: {user_input}

Provide a clear, helpful response:"""


SYNTHESIS_PROMPT = """Based on your reflection and the tool results, provide a comprehensive response.

Your thinking:
{reflection}

Tool results:
{tool_results}

User query: {user_input}

Synthesize this information into a clear, helpful response:"""


# ============================================================================
# LANGGRAPH AGENT
# ============================================================================

class LangGraphAgent(AgentBase):
    """
    LangGraph-based agent with reflection, tool use, and streaming.
    Integrates seamlessly with the concurrent console architecture.
    """
    
    def __init__(
        self,
        name: str,
        model: str,
        console: Console,
        provider: str = "openai",
        tools: Optional[List[str]] = None,
        show_thinking: bool = True,
        temperature: float = 0.7
    ):
        """
        Initialize LangGraph agent.
        
        Args:
            name: Agent name
            model: Model identifier
            console: Console instance
            provider: LLM provider ("openai", "anthropic", "google")
            tools: List of tool names to enable (None = all tools)
            show_thinking: Whether to display thinking process
            temperature: LLM temperature
        """
        super().__init__(name, model, console)
        
        self.provider = provider
        self.show_thinking = show_thinking
        self.temperature = temperature
        
        # Create LLM instance with streaming
        self.llm = LLMProvider.create(provider, model, streaming=True, temperature=temperature)
        
        # Setup tools
        if tools is None:
            self.tools = list(AVAILABLE_TOOLS.values())
            self.tool_names = list(AVAILABLE_TOOLS.keys())
        else:
            self.tools = [AVAILABLE_TOOLS[t] for t in tools if t in AVAILABLE_TOOLS]
            self.tool_names = tools
        
        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools) if self.tools else self.llm
        
        # Create graph
        self.graph = self._create_graph()
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("reflect", self._reflect_node)
        workflow.add_node("decide", self._decide_node)
        workflow.add_node("use_tools", self._use_tools_node)
        workflow.add_node("direct_response", self._direct_response_node)
        workflow.add_node("synthesize", self._synthesize_node)
        
        # Add edges
        workflow.set_entry_point("reflect")
        workflow.add_edge("reflect", "decide")
        
        # Conditional routing from decide
        workflow.add_conditional_edges(
            "decide",
            self._should_use_tools,
            {
                "use_tools": "use_tools",
                "direct_response": "direct_response",
            }
        )
        
        # Tool path
        workflow.add_edge("use_tools", "synthesize")
        workflow.add_edge("synthesize", END)
        
        # Direct path
        workflow.add_edge("direct_response", END)
        
        return workflow.compile()
    
    async def _reflect_node(self, state: AgentState) -> Dict[str, Any]:
        """Reflection/thinking node - analyze the query."""
        user_input = state["user_input"]
        
        prompt = REFLECTION_PROMPT.format(user_input=user_input)
        # Use HumanMessage instead of SystemMessage for better compatibility with Gemini
        messages = [HumanMessage(content=prompt)]
        
        reflection = ""
        
        # Stream the reflection
        if self.show_thinking:
            async for chunk in self.llm.astream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    reflection += chunk.content
        else:
            # Non-streaming if thinking is hidden
            response = await self.llm.ainvoke(messages)
            reflection = response.content
        
        return {
            "reflection": reflection,
            "iteration": state.get("iteration", 0) + 1
        }
    
    async def _decide_node(self, state: AgentState) -> Dict[str, Any]:
        """Decision node - determine if tools are needed."""
        reflection = state["reflection"]
        user_input = state["user_input"]
        
        tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in self.tools])
        
        prompt = DECISION_PROMPT.format(
            reflection=reflection,
            user_input=user_input,
            tools=tools_desc if self.tools else "No tools available"
        )
        
        # Use HumanMessage for better compatibility with Gemini
        messages = [HumanMessage(content=prompt)]
        
        # Get decision (non-streaming for structured output)
        response = await self.llm.ainvoke(messages)
        
        try:
            # Parse JSON response
            decision_text = response.content.strip()
            # Extract JSON if wrapped in markdown code blocks
            if "```json" in decision_text:
                decision_text = decision_text.split("```json")[1].split("```")[0].strip()
            elif "```" in decision_text:
                decision_text = decision_text.split("```")[1].split("```")[0].strip()
            
            decision = json.loads(decision_text)
            need_tools = decision.get("need_tools", False) and len(self.tools) > 0
        except:
            # Fallback if JSON parsing fails
            need_tools = False
        
        return {
            "need_tools": need_tools,
            "plan": decision.get("reasoning", "Direct response")
        }
    
    def _should_use_tools(self, state: AgentState) -> Literal["use_tools", "direct_response"]:
        """Router: determine next node based on tool decision."""
        return "use_tools" if state.get("need_tools", False) else "direct_response"
    
    async def _use_tools_node(self, state: AgentState) -> Dict[str, Any]:
        """Execute tools based on the plan."""
        user_input = state["user_input"]
        reflection = state["reflection"]
        
        # Ask LLM to make tool calls - use HumanMessage for Gemini compatibility
        messages = [
            HumanMessage(content=f"Based on this thinking:\n{reflection}\n\nUser query: {user_input}\n\nUse the available tools to help answer."),
        ]
        
        response = await self.llm_with_tools.ainvoke(messages)
        
        tool_results = []
        
        # Execute tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                # Find and execute the tool
                for tool in self.tools:
                    if tool.name == tool_name:
                        try:
                            # Execute tool
                            if isinstance(tool_args, dict):
                                # Extract first argument value
                                arg_value = list(tool_args.values())[0] if tool_args else ""
                            else:
                                arg_value = str(tool_args)
                            
                            result = tool.func(arg_value)
                            tool_results.append(f"{tool_name}({arg_value}) = {result}")
                        except Exception as e:
                            tool_results.append(f"{tool_name}: Error - {str(e)}")
                        break
        
        return {"tool_results": tool_results}
    
    async def _direct_response_node(self, state: AgentState) -> Dict[str, Any]:
        """Generate direct response without tools."""
        reflection = state["reflection"]
        user_input = state["user_input"]
        
        prompt = DIRECT_RESPONSE_PROMPT.format(
            reflection=reflection,
            user_input=user_input
        )
        
        # Use HumanMessage for Gemini compatibility
        messages = [HumanMessage(content=prompt)]
        
        response = ""
        async for chunk in self.llm.astream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                response += chunk.content
        
        return {"final_response": response}
    
    async def _synthesize_node(self, state: AgentState) -> Dict[str, Any]:
        """Synthesize tool results into final response."""
        reflection = state["reflection"]
        user_input = state["user_input"]
        tool_results = state.get("tool_results", [])
        
        tool_results_text = "\n".join(tool_results) if tool_results else "No results"
        
        prompt = SYNTHESIS_PROMPT.format(
            reflection=reflection,
            tool_results=tool_results_text,
            user_input=user_input
        )
        
        # Use HumanMessage for Gemini compatibility
        messages = [HumanMessage(content=prompt)]
        
        response = ""
        async for chunk in self.llm.astream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                response += chunk.content
        
        return {"final_response": response}
    
    async def process(self, message: Message) -> None:
        """
        Process a message and respond using LangGraph workflow.
        Integrates with console's concurrent streaming architecture.
        
        Args:
            message: Incoming message to process
        """
        # Add to history
        self.add_to_history("user", message.content)
        
        # Initialize state
        initial_state = {
            "messages": [HumanMessage(content=message.content)],
            "user_input": message.content,
            "reflection": "",
            "plan": "",
            "need_tools": False,
            "tool_results": [],
            "final_response": "",
            "iteration": 0
        }
        
        try:
            # Track current phase for streaming
            current_phase = None
            thinking_message_id = None
            response_message_id = None
            
            # Stream through the graph
            async for event in self.graph.astream_events(initial_state, version="v1"):
                event_type = event.get("event")
                
                # Handle streaming chunks from LLM
                if event_type == "on_chat_model_stream":
                    data = event.get("data", {})
                    chunk = data.get("chunk")
                    
                    if chunk and hasattr(chunk, 'content') and chunk.content:
                        # Determine which phase we're in based on the tags
                        tags = event.get("tags", [])
                        name = event.get("name", "")
                        
                        # Reflection phase
                        if "reflect" in str(tags) or "reflect" in name:
                            if self.show_thinking:
                                if thinking_message_id is None:
                                    thinking_message_id = self.console.start_agent_message(
                                        self.name,
                                        receivers=["user"]
                                    )
                                    self.console.update_agent_message(thinking_message_id, "🤔 **Thinking:** ")
                                
                                self.console.update_agent_message(thinking_message_id, chunk.content)
                        
                        # Response phase (direct or synthesis)
                        elif "direct_response" in str(tags) or "synthesize" in str(tags) or \
                             "direct_response" in name or "synthesize" in name:
                            if response_message_id is None:
                                # Complete thinking message if it exists
                                if thinking_message_id is not None:
                                    self.console.complete_agent_message(thinking_message_id)
                                
                                response_message_id = self.console.start_agent_message(
                                    self.name,
                                    receivers=["user"]
                                )
                                self.console.update_agent_message(response_message_id, "💬 **Response:** ")
                            
                            self.console.update_agent_message(response_message_id, chunk.content)
            
            # Get final state
            final_state = await self.graph.ainvoke(initial_state)
            
            # Complete any open messages
            if thinking_message_id is not None and self.show_thinking:
                self.console.complete_agent_message(thinking_message_id)
            
            if response_message_id is not None:
                self.console.complete_agent_message(response_message_id)
            elif final_state.get("final_response"):
                # Fallback if streaming didn't capture the response
                response_message_id = self.console.start_agent_message(
                    self.name,
                    receivers=["user"]
                )
                self.console.update_agent_message(
                    response_message_id,
                    "💬 **Response:** " + final_state["final_response"]
                )
                self.console.complete_agent_message(response_message_id)
            
            # Display tool results if any
            if final_state.get("tool_results"):
                tool_msg_id = self.console.start_agent_message(
                    self.name,
                    receivers=["user"]
                )
                tool_text = "🔧 **Tools Used:**\n" + "\n".join(final_state["tool_results"])
                self.console.update_agent_message(tool_msg_id, tool_text)
                self.console.complete_agent_message(tool_msg_id)
            
            # Add to history
            self.add_to_history("assistant", final_state.get("final_response", ""))
            
        except Exception as e:
            # Error handling
            error_msg_id = self.console.start_agent_message(
                self.name,
                receivers=["user"]
            )
            self.console.update_agent_message(
                error_msg_id,
                f"❌ **Error:** {str(e)}"
            )
            self.console.complete_agent_message(error_msg_id)
            raise
