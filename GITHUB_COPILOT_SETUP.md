# Using GitHub Copilot as LLM Provider

GitHub Copilot provides free access to GPT-4 and GPT-3.5-turbo models without quota limits for Copilot subscribers!

## Quick Setup

### Option 1: Automatic Setup (Recommended)

```bash
python setup_github_token.py
```

This will guide you through getting and saving your GitHub token.

### Option 2: Manual Setup

1. **Get your GitHub Copilot token:**

   In VS Code:
   - Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
   - Type: `GitHub Copilot: Get Token`
   - Copy the token

2. **Add to .env file:**

   ```bash
   # Create .env from template
   copy .env.example .env
   
   # Edit .env and add your token
   GITHUB_TOKEN=gho_your_token_here
   ```

3. **Run the application:**

   ```bash
   python main.py
   ```

## Available Models

GitHub Copilot provides access to:
- **gpt-4** - Most capable model
- **gpt-3.5-turbo** - Faster, good for simpler tasks

## Agent Configuration

The current setup creates 7 agents:
- **Alice, Bob, Charlie, Grace**: Using GPT-4 (more intelligent)
- **Diana, Eve, Frank**: Using GPT-3.5-turbo (faster)

All agents have:
- ✅ Reflection/thinking capabilities
- ✅ Tool access (calculator, datetime, search)
- ✅ Concurrent streaming
- ✅ No quota limits (with Copilot subscription)

## Troubleshooting

### Token not working?

1. Make sure you have an active GitHub Copilot subscription
2. Try regenerating the token in VS Code
3. Check that the token starts with `gho_`

### API errors?

GitHub Copilot API uses OpenAI-compatible endpoints:
- Base URL: `https://api.githubcopilot.com`
- Same models as OpenAI (gpt-4, gpt-3.5-turbo)

## Benefits

✅ **No quota limits** - Unlimited usage with Copilot subscription  
✅ **Free with subscription** - No additional API costs  
✅ **Same models** - Access to GPT-4 and GPT-3.5-turbo  
✅ **Fast** - Good performance and reliability  

## Commands

Once running:
- Type messages to broadcast to all 7 agents
- Use `@Alice message` to send to specific agents
- Type `agents` to see all available agents
- Type `exit` to quit
