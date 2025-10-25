# Quick Test: Scrolling Demo

## How to Test Scrolling

1. **Start the application:**
   ```bash
   python main.py
   ```

2. **Generate some messages (need >10 for scrolling):**
   ```
   You > Hello world
   You > What is Python?
   You > Tell me about AI
   You > Explain machine learning
   You > What is deep learning?
   You > Tell me about neural networks
   You > What is NLP?
   You > Explain transformers
   You > What is GPT?
   You > Tell me about agents
   You > What is prompt engineering?
   You > Explain embeddings
   ```
   
   (Each message will get 3 agent responses, creating 36+ messages total)

3. **Now try scrolling:**
   ```
   You > up        ← Scroll up 1 message
   You > up        ← Scroll up another
   You > up        ← Keep going
   You > pageup    ← Jump up 10 messages
   You > top       ← Jump to very first message
   You > down      ← Scroll down 1 message
   You > pagedown  ← Jump down 10 messages
   You > bottom    ← Return to latest (auto-scroll ON)
   ```

4. **Watch the status bar:**
   ```
   ╭──────────────────────────────────────────────────╮
   │ Queue: 36 messages  Streaming: 0                │
   │ Viewing: 10-20 of 36  [SCROLL: offset=16]       │
   ╰──────────────────────────────────────────────────╯
   ```

## What You'll See

### Before Scrolling (Auto-Scroll ON)
```
┌─ Status ─────────────────────────────────────────┐
│ Queue: 36 messages  Streaming: 0                 │
│ Viewing: 27-36 of 36  [AUTO-SCROLL ON]           │
└──────────────────────────────────────────────────┘

┌─ 👤 user → ALL (14:23:45) ───────────────────────┐
│ What is prompt engineering?                      │
└──────────────────────────────────────────────────┘

┌─ 🤖 GPT-4 → user (14:23:46) ─────────────────────┐
│ Prompt engineering is the art of...             │
└──────────────────────────────────────────────────┘

... (showing latest 10 messages)
```

### After Typing "up" 5 Times
```
┌─ Status ─────────────────────────────────────────┐
│ Queue: 36 messages  Streaming: 0                 │
│ Viewing: 22-31 of 36  [SCROLL: offset=5]         │
└──────────────────────────────────────────────────┘

┌─ 👤 user → ALL (14:23:40) ───────────────────────┐
│ What is deep learning?                           │
└──────────────────────────────────────────────────┘

┌─ 🤖 GPT-4 → user (14:23:41) ─────────────────────┐
│ Deep learning is a subset of...                 │
└──────────────────────────────────────────────────┘

... (showing messages 22-31, older than before)
```

### After Typing "top"
```
┌─ Status ─────────────────────────────────────────┐
│ Queue: 36 messages  Streaming: 0                 │
│ Viewing: 1-10 of 36  [SCROLL: offset=26]         │
└──────────────────────────────────────────────────┘

┌─ 👤 user → ALL (14:23:00) ───────────────────────┐
│ Hello world                                      │
└──────────────────────────────────────────────────┘

┌─ 🤖 GPT-4 → user (14:23:01) ─────────────────────┐
│ Hello! I'm GPT-4. How can I help you?           │
└──────────────────────────────────────────────────┘

... (showing first 10 messages)
```

### After Typing "bottom"
```
┌─ Status ─────────────────────────────────────────┐
│ Queue: 36 messages  Streaming: 0                 │
│ Viewing: 27-36 of 36  [AUTO-SCROLL ON]           │
└──────────────────────────────────────────────────┘

(Back to showing latest messages)
(Auto-scroll re-enabled)
```

## Key Points

1. **Commands are typed at the input prompt** - not mouse wheel
2. **Display updates automatically** - thanks to 10 FPS refresh loop
3. **Status bar shows your position** - always know where you are
4. **Auto-scroll toggles smartly** - OFF when scrolling up, ON at bottom
5. **No manual refresh needed** - changes appear immediately

## Why This Design?

- ✅ Works on all terminals (Windows, Linux, Mac)
- ✅ No complex mouse event handling
- ✅ Simple, predictable user experience
- ✅ Integrates seamlessly with Rich Console
- ✅ Compatible with existing command structure

## Future: Mouse Support

If you want actual mouse wheel scrolling, you'd need to:
1. Replace Rich Console with prompt_toolkit or blessed
2. Handle terminal mouse events
3. Refactor input handling significantly

Current keyboard approach is production-ready and user-friendly!
