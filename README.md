# AutoStream Social-to-Lead Agent

An intelligent conversational AI agent built with **LangGraph** that transforms social media interactions into qualified leads for AutoStream, an AI-powered video editing SaaS platform.

---

## 📑 Table of Contents

- [Features](#features)
- [How to Run the Project Locally](#how-to-run-the-project-locally)
- [Architecture Explanation](#architecture-explanation)
- [WhatsApp Deployment via Webhooks](#whatsapp-deployment-via-webhooks)
- [Project Structure](#project-structure)
- [Technologies Used](#technologies-used)

---

##Features

- **Intent Classification**: Automatically detects user intent (greeting, inquiry, high-intent)
- **RAG-Powered Knowledge Base**: Retrieves accurate product information using ChromaDB vector search
- **Multi-Turn Lead Collection**: Conversationally gathers name, email, and platform across multiple interactions
- **Smart Data Extraction**: Uses LLM to intelligently extract information from natural language
- **State Management**: Maintains conversation context across all turns using LangGraph state

---

##How to Run the Project Locally

### Prerequisites

- Python 3.11 or higher
- Google Gemini API key ([Get one free here](https://ai.google.dev/))

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd Project
```

### Step 2: Create a Virtual Environment (Recommended)

**Using conda:**
```bash
conda create -n autostream-env python=3.11 -y
conda activate autostream-env
```

**Using venv:**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies include:**
- `langchain` & `langgraph` - Orchestration framework
- `langchain-google-genai` - Google Gemini LLM integration
- `chromadb` - Vector database for RAG
- `sentence-transformers` - Embeddings model
- `python-dotenv` - Environment variable management

### Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# .env
GOOGLE_API_KEY=your_api_key_here
MODEL_NAME=gemini-2.5-flash
TEMPERATURE=0.7
LLM_PROVIDER=google
```

**Get your API key:**
1. Visit [Google AI Studio](https://ai.google.dev/)
2. Click "Get API Key"
3. Copy and paste into `.env`

### Step 5: Run the Agent

```bash
python main.py
```

### Example Interaction

```
Initializing AutoStream Agent...
Agent Ready! (Type 'quit' to exit)
---------------------------------------

You: Hi there!
Agent: Hello! Welcome to AutoStream! I'm here to help you discover how our 
AI-powered video editing platform can save you time...

You: What are your pricing plans?
Agent: We offer two plans:

**Basic Plan** - $29/month
- 10 videos per month
- 720p resolution
...

You: I want to try the Pro plan for my YouTube channel
Agent: That's fantastic! I'd love to help you get started. What's your name?

You: Sarah Martinez
Agent: Perfect! What's your email address?

You: sarah@example.com
Agent: Perfect! Thank you, Sarah Martinez!

I've registered your interest in AutoStream...
```

---

##Architecture Explanation

### Why LangGraph is chosen

**LangGraph** was selected as the orchestration framework for several critical reasons:

1. **State Management**: LangGraph provides built-in, immutable state management across conversation turns. Traditional chatbots often struggle with maintaining context across multi-step interactions. LangGraph's `StateGraph` automatically persists conversation history, collected lead data, and current intent, eliminating manual state tracking bugs.

2. **Conditional Routing**: The agent needs to dynamically route conversations based on user intent. LangGraph's conditional edges allow seamless transitions between greeting handlers, RAG-powered inquiry nodes, and multi-turn lead collection flows—all without complex if-else chains.

3. **Modularity & Testability**: Each node (classify_intent, handle_inquiry, collect_lead_data) is an isolated function, making the workflow easy to test, debug, and extend. Adding new conversation paths requires simply adding new nodes and edges.

4. **Cyclic Workflows**: Unlike linear LLM chains, LangGraph supports cycles, enabling the agent to loop through lead collection across multiple turns until all required fields (name, email, platform) are gathered.

5. **Visualization & Debugging**: LangGraph's graph structure makes the agent's decision flow transparent and auditable—critical for understanding why specific responses were generated.

### How State is Managed

The agent maintains a **typed state dictionary** throughout the conversation:

```python
class AgentState(TypedDict):
    messages: List[str]           # Full conversation history
    user_message: str             # Current input
    intent: str                   # Classified intent (greeting/inquiry/high_intent)
    rag_context: str              # Retrieved knowledge from vector DB
    lead_data: dict               # Collected fields: {name, email, platform}
    awaiting_field: str           # Current field being collected
    response: str                 # Agent's generated response
```

**State Flow:**
1. **Initialization**: Each turn creates or updates the state with the new user message
2. **Node Processing**: Each node (e.g., `classify_intent_node`) receives the current state, processes it, and returns an updated state
3. **Persistence**: LangGraph automatically propagates state changes through the graph
4. **Routing**: Conditional edges read the state (e.g., `intent` field) to determine the next node
5. **Multi-Turn Memory**: The `messages` list accumulates all turns, while `awaiting_field` tracks the lead collection progress across multiple interactions

This architecture enables:
- **Contextual responses** (the agent "remembers" previous questions)
- **Progressive disclosure** (lead collection happens conversationally, not in a rigid form)
- **Error recovery** (users can cancel or correct information mid-flow)

---

##WhatsApp Deployment via Webhooks

### Integration Architecture

To deploy this agent on **WhatsApp**, we would leverage the **WhatsApp Business API** with webhook-based message handling:

```
WhatsApp User → WhatsApp Business API → Webhook Endpoint (FastAPI Server)
                                              ↓
                                    AutoStreamAgent.run()
                                              ↓
                                    Response → WhatsApp Business API → User
```

### Implementation Steps

#### 1. Set Up WhatsApp Business API

1. Create a **Meta Business account** and register your app
2. Add **WhatsApp product** to your app
3. Configure webhook URL (e.g., `https://yourdomain.com/webhook/whatsapp`)
4. Verify webhook with the provided token
5. Subscribe to message events (`messages`, `message_status`)

#### 2. Create FastAPI Webhook Server

```python
# whatsapp_webhook.py
from fastapi import FastAPI, Request
from agent.workflow import AutoStreamAgent
from langchain_google_genai import ChatGoogleGenerativeAI
import os

app = FastAPI()

# Initialize agent once at startup
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)
agent = AutoStreamAgent(llm)

# Store conversation states per user (use Redis in production)
user_states = {}

@app.get("/webhook/whatsapp")
async def verify_webhook(request: Request):
    """Verify webhook during Meta setup"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == os.getenv("WEBHOOK_VERIFY_TOKEN"):
        return int(challenge)
    return {"error": "Invalid token"}, 403

@app.post("/webhook/whatsapp")
async def handle_message(request: Request):
    """Process incoming WhatsApp messages"""
    data = await request.json()
    
    # Extract message details
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            
            if "messages" in value:
                message = value["messages"][0]
                user_phone = message["from"]  # User's phone number
                user_message = message["text"]["body"]
                
                # Get or initialize user state
                state = user_states.get(user_phone)
                
                # Run agent
                result = agent.run(user_message, state)
                user_states[user_phone] = result  # Save state
                
                # Send response back to WhatsApp
                send_whatsapp_message(user_phone, result["response"])
    
    return {"status": "ok"}

def send_whatsapp_message(phone_number: str, message: str):
    """Send message via WhatsApp Business API"""
    import requests
    
    url = f"https://graph.facebook.com/v17.0/{os.getenv('PHONE_NUMBER_ID')}/messages"
    headers = {
        "Authorization": f"Bearer {os.getenv('WHATSAPP_ACCESS_TOKEN')}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "text": {"body": message}
    }
    
    requests.post(url, json=payload, headers=headers)
```

#### 3. Deploy to Production

**Option A: Cloud Deployment (Recommended)**
```bash
# Deploy to Railway/Render/Heroku
pip install gunicorn
gunicorn whatsapp_webhook:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**Option B: Ngrok for Testing**
```bash
# Run locally with ngrok tunnel
uvicorn whatsapp_webhook:app --port 8000
ngrok http 8000
# Use ngrok URL (https://xxxx.ngrok.io/webhook/whatsapp) in Meta settings
```

#### 4. Environment Variables for Production

```bash
# .env (production)
GOOGLE_API_KEY=your_gemini_key
WEBHOOK_VERIFY_TOKEN=your_custom_token_123
WHATSAPP_ACCESS_TOKEN=your_meta_access_token
PHONE_NUMBER_ID=your_whatsapp_phone_id
```

### Key Considerations

- **State Persistence**: Use **Redis** or **MongoDB** to store `user_states` across server restarts
- **Rate Limiting**: WhatsApp has message rate limits—implement queuing with Celery
- **Media Handling**: Extend webhook to handle images/videos (e.g., users sending content samples)
- **Session Timeout**: Clear stale states after 24 hours of inactivity
- **Security**: Validate webhook signatures using Meta's signature verification

### Benefits of This Architecture

✅ **Scalable**: Same agent code works across WhatsApp, web chat, Telegram  
✅ **Stateful**: Maintains conversation context even if server restarts (with Redis)  
✅ **Fast**: Webhook-based (real-time responses vs polling)  
✅ **Cost-Effective**: Only pay for API calls when users message you  

---

##Project Structure

```
Project/
├── main.py                      # Entry point - CLI interface
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (API keys)
├── agent/
│   ├── workflow.py              # LangGraph orchestration & state machine
│   └── conversation.py          # (Reserved for future enhancements)
├── src/
│   ├── utils/
│   │   ├── intent_classifier.py # LLM-based intent detection
│   │   └── rag_pipeline.py      # Vector DB + retrieval logic
│   └── tools/
│       └── lead_capture.py      # Multi-turn lead collection
├── data/
│   └── autostream_knowledge.json # Product knowledge base
├── chroma_db/                   # Vector database (auto-generated)
```

---

##Technologies Used

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **LLM** | Google Gemini 2.5 Flash | Intent classification, response generation, data extraction |
| **Orchestration** | LangGraph | State management & workflow routing |
| **Vector DB** | ChromaDB | Semantic search for RAG pipeline |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 | Document & query embeddings |
| **Framework** | LangChain | LLM integrations & prompt management |
| **Environment** | python-dotenv | Secure API key management |

---

##Workflow Diagram

```
User Input
    ↓
[Classify Intent Node]
    ↓
    ├─→ Greeting → [Handle Greeting] → Response
    ├─→ Inquiry → [Handle Inquiry (RAG)] → Response
    └─→ High Intent → [Start Lead Collection]
                            ↓
                    [Collect Lead Data (Multi-turn)]
                            ↓
                    [All fields complete?]
                            ↓
                    [Capture Lead Tool] → Success Message
```
