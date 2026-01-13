"""
Conversation Manager for AutoStream Agent
Handles session management and conversation flow
"""

import os
import sys

# --- Telemetry Suppression ---
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_ANONYMOUS"] = "False"
os.environ["SCARF_NO_ANALYTICS"] = "true"

from typing import Optional
from dotenv import load_dotenv

# LLM imports - ONLY Google Gemini
from langchain_google_genai import ChatGoogleGenerativeAI

# Add project root to path to ensure imports work if run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.workflow import AutoStreamAgent


class ConversationManager:
    """Manages agent conversations with state persistence"""
    
    def __init__(self):
        """
        Initialize conversation manager strictly for Gemini
        """
        load_dotenv()
        
        # Verify API Key exists before crashing
        if not os.getenv("GOOGLE_API_KEY"):
            print("\n❌ CRITICAL ERROR: GOOGLE_API_KEY is missing from .env file!")
            print("Please create a .env file with your API key.\n")
            sys.exit(1)

        self.llm = self._initialize_llm()
        
        try:
            self.agent = AutoStreamAgent(self.llm)
        except Exception as e:
            print(f"\n Error initializing Agent: {e}")
            print("Ensure 'data/autostream_knowledge.json' exists in the project root.")
            sys.exit(1)
            
        self.state = None
        self.turn_count = 0
    
    def _initialize_llm(self):
        """Initialize Google Gemini 1.5 Flash"""
        
        model = os.getenv("MODEL_NAME", "gemini-1.5-flash")
        temperature = float(os.getenv("TEMPERATURE", "0.7"))
        api_key = os.getenv("GOOGLE_API_KEY")

        print(f"✓ Initializing Gemini Model: {model}")

        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=api_key
        )
    
    def send_message(self, user_message: str) -> str:
        """
        Send a message to the agent and get response
        """
        self.turn_count += 1
        
        # Run agent with current state
        self.state = self.agent.run(user_message, self.state)
        
        # Return the response string from the state
        return self.state["response"]
    
    def reset(self):
        """Reset conversation state"""
        self.state = None
        self.turn_count = 0
        if hasattr(self.agent, 'reset'):
            self.agent.reset()
    
    def get_conversation_history(self) -> list:
        """Get the conversation history"""
        if self.state and "messages" in self.state:
            return self.state["messages"]
        return []


def run_interactive_demo():
    """Run an interactive demo of the agent"""
    print("=" * 70)
    print("  AutoStream AI Agent - Social-to-Lead Demo (Gemini Edition)")
    print("=" * 70)
    print("\nWelcome! I'm the AutoStream AI assistant.")
    print("I can help you learn about our video editing platform and get started.")
    print("\nType 'quit' or 'exit' to end the conversation.")
    print("Type 'reset' to start a new conversation.")
    print("=" * 70)
    
    try:
        manager = ConversationManager()
        print()
    except Exception as e:
        print(f"\n✗ Error initializing: {e}")
        return
    
    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            # Check for commands
            if user_input.lower() in ['quit', 'exit']:
                print("\nThank you for chatting with AutoStream! Goodbye!")
                break
            
            if user_input.lower() == 'reset':
                manager.reset()
                print("\n[Conversation reset. Starting fresh!]\n")
                continue
            
            # Send message to agent
            print("\nAgent: ", end="", flush=True)
            response = manager.send_message(user_input)
            print(response)
            
            # Show debug info (optional)
            if os.getenv("DEBUG", "false").lower() == "true":
                print(f"\n[DEBUG] Intent: {manager.state.get('intent', 'N/A')}")
                
        except KeyboardInterrupt:
            print("\n\nConversation interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n✗ Error: {e}")
            print("Please try again or type 'reset' to start over.")


if __name__ == "__main__":
    run_interactive_demo()