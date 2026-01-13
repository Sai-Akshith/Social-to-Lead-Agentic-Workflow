# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### Create Conda Environment (Windows)
If you're using Anaconda, create a dedicated environment for this project to avoid conflicts.

```cmd
:: Open Anaconda Prompt (recommended) OR initialize conda in cmd:
conda init cmd
:: close and reopen your cmd after init

:: 1) Create environment (Python 3.11 recommended)
conda create -n autostream-env python=3.11 -y

:: 2) Activate environment
conda activate autostream-env

:: 3) Upgrade pip and certifi (helps with SSL issues)
python -m pip install --upgrade pip certifi

:: 4) Install project dependencies
cd V:\GenAI-Project-ServiceHive
pip install -r requirements.txt
```

If you encounter SSL certificate errors during pip install:

```cmd
:: Reinstall/upgrade certificates
python -m pip install --upgrade certifi
python -c "import certifi; print(certifi.where())"
```
Use the printed path as the CA bundle if needed.

### 2. Set Up API Key
Create a `.env` file:
```bash
LLM_PROVIDER=google
GOOGLE_API_KEY=your_api_key_here
MODEL_NAME=gemini-1.5-flash
TEMPERATURE=0.7
```

**Get a free API key:**
- Google Gemini: https://makersuite.google.com/app/apikey
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/

### 3. Run the Agent
```bash
python main.py
```

### 4. Try This Conversation
```
You: Hi there!
[Agent greets you]

You: What are your pricing plans?
[Agent retrieves info from knowledge base]

You: That sounds great! I want to try the Pro plan for my YouTube channel
[Agent detects high intent and starts collecting info]

You: Sarah Martinez
[Agent asks for email]

You: sarah@example.com
[Agent captures lead - mission complete! 🎉]
```

## 🎥 Record Demo Video

Run the pre-scripted demo:
```bash
python demo_script.py
```

This shows:
- ✓ RAG retrieval in action
- ✓ Intent detection across conversation
- ✓ Multi-turn lead collection
- ✓ Successful tool execution

## 🧪 Run Tests
```bash
python -m pytest tests/ -v
# or
python tests/test_agent.py
```

## 📁 Project Structure
```
GenAI-Project-ServiceHive/
├── main.py              # Run this to start
├── demo_script.py       # Run this for demo video
├── data/                # Knowledge base
├── src/
│   ├── agent/          # LangGraph workflow
│   ├── tools/          # Lead capture
│   └── utils/          # RAG + Intent classifier
└── tests/              # Unit tests
```

## 🐛 Troubleshooting

**No module named 'src'**
```bash
# Make sure you're in the project root
cd GenAI-Project-ServiceHive
python main.py
```

**API Key Error**
```bash
# Check your .env file exists and has the right key
type .env  # Windows
# cat .env  # Linux/Mac
```

**Import errors**
```bash
pip install -r requirements.txt --upgrade
```

## 📊 Assignment Checklist

- [x] Intent detection (greeting/inquiry/high-intent) ✓
- [x] RAG-powered knowledge retrieval ✓
- [x] Multi-turn lead collection ✓
- [x] Tool execution (mock_lead_capture) ✓
- [x] State management (5-6 turns) ✓
- [x] LangGraph framework ✓
- [x] Clean code structure ✓
- [x] requirements.txt ✓
- [x] README.md with architecture ✓
- [x] WhatsApp deployment strategy ✓

**Next Steps:**
1. Get your API key
2. Run `python main.py`
3. Test the conversation flow
4. Record your demo video using `python demo_script.py`
5. Push to GitHub

Good luck! 🚀
