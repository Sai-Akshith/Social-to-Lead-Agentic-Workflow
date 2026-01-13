"""
Main entry point for AutoStream Social-to-Lead Agent
"""
import sys
import os
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_google_genai import ChatGoogleGenerativeAI
from agent.workflow import AutoStreamAgent

# --- OPTIONAL: Supress ChromaDB Telemetry Warnings ---
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_ANONYMOUS"] = "False"

def main():
    load_dotenv()
    
    # Initialize LLM
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY not found in .env")
        return

    print("Initializing AutoStream Agent...")
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)
        agent = AutoStreamAgent(llm)
        
        print("\nAgent Ready! (Type 'quit' to exit)")
        print("---------------------------------------")
        
        # Interactive Loop
        state = None
        while True:
            try:
                user_input = input("\nYou: ")
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                # Run Agent
                result = agent.run(user_input, state)
                state = result # Update state for next turn
                
                # Print Response
                print(f"Agent: {result['response']}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error during conversation: {e}")
                
    except Exception as e:
        print(f"\nCritical Error initializing Agent: {e}")
        print("Try running: pip install --upgrade langchain-google-genai")

if __name__ == "__main__":
    main()