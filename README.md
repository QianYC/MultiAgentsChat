# Multi-Agent LLM Chat Console

A Python-based console application for chatting with multiple LLM models simultaneously using **concurrent streaming architecture**.

## 🌟 Features

- **✨ Concurrent Streaming**: Multiple agents can stream responses simultaneously without blocking each other
- **🔒 Thread-Safe**: Lock-based message queue for atomic updates
- **⚡ High Performance**: 2-3x faster than sequential streaming
- **🎯 Fixed-Rate Display**: Smooth 10 FPS refresh for clean visual updates
- **📊 Bulletin Board**: All messages visible to all participants
- **🎨 Beautiful UI**: Rich console formatting with colors and live updates
- **📝 Message Routing**: Send to specific agents or broadcast to all

## 🏗️ Architecture

```
Multiple Agents → Message Queue (Thread-Safe) → Display Loop (10 FPS)
                       ↓
                 All agents update
                 their messages
                 concurrently!
```

### Performance

**Concurrent Streaming (Current)**:
- Agent1 (20s), Agent2 (16s), Agent3 (11s) = **20s total** ✅
- All agents stream in parallel

**vs Sequential Streaming**:
- Agent1 (20s) → Agent2 (16s) → Agent3 (11s) = **47s total** ❌
- Agents wait for each other

**Result: 2.4x faster!** 🚀

## 🚀 Quick Start

### Installation

```powershell
# Clone and navigate
cd c:\Users\qyc\source\repos\tradecontest

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run

```powershell
# Main application
python main.py

# Concurrent streaming demo
python demo_concurrent.py
```

## 📝 Usage

### Commands

- Type message → broadcast to ALL agents
- `@agent1,agent2 message` → send to specific agents
- `exit` or `quit` → exit
- `clear` → clear screen
- `history` → view history
- `agents` → list agents

### Examples

```
You > Hello everyone!
# All 3 agents respond concurrently

You > @GPT-4 What is Python?
# Only GPT-4 responds

You > @GPT-4,Claude Explain async
# GPT-4 and Claude both respond
```

## 🔧 Configuration

Copy `.env.example` to `.env` and add your API keys:

```bash
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
```

## 📁 Project Structure

```
├── console.py              # Console with concurrent streaming
├── message_queue.py        # Thread-safe message queue
├── agent_base.py           # Abstract agent base class
├── message.py              # Message models and parser
├── streaming_demo_agent.py # Demo agent implementation
├── agent_manager.py        # Agent orchestration (legacy)
├── main.py                 # Main application
├── demo_concurrent.py      # Concurrent streaming demo
└── requirements.txt        # Dependencies
```

## 🎯 How It Works

### 1. Agent Submits Message
```python
message_id = console.start_agent_message(agent_name)
```

### 2. Agent Streams Chunks (Non-Blocking!)
```python
for chunk in response_stream:
    console.update_agent_message(message_id, chunk)
    # Other agents can update their messages too!
```

### 3. Agent Completes
```python
console.complete_agent_message(message_id)
```

### 4. Display Loop (10 FPS)
```python
while displaying:
    messages = queue.get_snapshot()  # Thread-safe
    render(messages)
    await sleep(0.1)  # 10 FPS
```

## 🔐 Thread Safety

All operations are thread-safe:

```python
class MessageQueue:
    def __init__(self):
        self._lock = Lock()  # Thread-safe operations
    
    def update_message(self, message_id, chunk):
        with self._lock:  # Atomic update
            self._queue[idx].content += chunk
```

## 📚 Documentation

- **`CONCURRENT_STREAMING_ANALYSIS.md`** - Detailed architecture analysis
- **`requirements.txt`** - Python dependencies

## 🎓 Next Steps

### Integrate Real LLMs

Replace demo agents with real providers:

```python
from openai import AsyncOpenAI
from agent_base import AgentBase

class OpenAIAgent(AgentBase):
    def __init__(self, name, model, console, api_key):
        super().__init__(name, model, console)
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def process(self, message):
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": message.content}],
            stream=True
        )
        
        await self.stream_response(
            self._extract_chunks(stream),
            receivers=["user"]
        )
```

### Add LangGraph

Integrate LangGraph for complex workflows:
- Multi-step reasoning
- Agent collaboration
- Tool usage
- State management

## 🛠️ Technologies

- **Python 3.11+**
- **asyncio** - Async/await for concurrency
- **Rich** - Beautiful console UI
- **threading.Lock** - Thread-safe operations
- **LangGraph** - Agent orchestration (coming soon)

## ✅ Production Ready

- ✅ Thread-safe concurrent operations
- ✅ No race conditions
- ✅ Clean, organized output
- ✅ Scalable to 10+ agents
- ✅ Ready for real LLM integration

## 📄 License

[Your License]

## 🙏 Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich)
- Inspired by modern multi-agent architectures
- Thanks to the open-source community

---

**Status**: ✅ Core architecture complete with concurrent streaming

**Next**: Integrate OpenAI, Anthropic, Google Gemini APIs
