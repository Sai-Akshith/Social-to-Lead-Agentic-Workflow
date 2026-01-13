"""
Intent Classification for Social-to-Lead Workflow
Classifies user messages into: greeting, inquiry, or high_intent
"""

from enum import Enum
from langchain_core.messages import HumanMessage, SystemMessage

class IntentType(Enum):
    """Types of user intent"""
    GREETING = "greeting"
    INQUIRY = "inquiry"
    HIGH_INTENT = "high_intent"

class IntentClassifier:
    """Classifies user intent using LLM-based prompting"""
    
    def __init__(self, llm):
        self.llm = llm
        self.system_prompt = """You are an expert at understanding user intent in sales conversations.

Classify the user's message into one of these categories:

1. GREETING - User is just saying hello or making casual conversation
   Examples: "Hi", "Hello", "How are you?", "Good morning"

2. INQUIRY - User is asking about products, features, pricing, or policies
   Examples: "Price?", "How much?", "What features?", "Refund policy?"

3. HIGH_INTENT - User is showing buying signals or readiness to sign up
   Examples: "I want to try this", "Sign me up", "I'd like to get started", "I want the Pro plan"

Respond with ONLY one word: greeting, inquiry, or high_intent"""
    
    def classify(self, user_message: str, conversation_history: list = None) -> IntentType:
        """Classify the user's intent"""
        # Build context
        context = ""
        if conversation_history:
            recent_messages = conversation_history[-2:] # Last turn only
            context = "\n".join([f"Msg: {msg}" for msg in recent_messages])
            context = f"\nRecent Context:\n{context}\n\n"
        
        # Classify
        try:
            response = self.llm.invoke([
                HumanMessage(content=self.system_prompt + "\n\n" + f"{context}Current User Message: {user_message}\n\nIntent:")
            ])
            intent_text = response.content.strip().lower()
            
            if "greeting" in intent_text:
                return IntentType.GREETING
            elif "high_intent" in intent_text or "high-intent" in intent_text:
                return IntentType.HIGH_INTENT
            else:
                return IntentType.INQUIRY
        except Exception:
            # Fallback to Inquiry if LLM fails
            return IntentType.INQUIRY