"""
LangGraph Workflow for Social-to-Lead Agent
Implements state management and orchestration
"""

from typing import TypedDict, Annotated, List, Literal
from operator import add
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.utils.intent_classifier import IntentClassifier, IntentType
from src.utils.rag_pipeline import AutoStreamRAG
from src.tools.lead_capture import LeadCollector


class AgentState(TypedDict):
    """State structure for the agent workflow"""
    messages: List[str]  # Conversation history
    user_message: str  # Current user message
    intent: str  # Detected intent (greeting, inquiry, high_intent)
    rag_context: str  # Retrieved context from RAG
    lead_data: dict  # Collected lead information
    awaiting_field: str  # Which field we're currently collecting
    response: str  # Agent's response
    next_action: str  # What to do next (respond, collect_data, capture_lead, end)


class AutoStreamAgent:
    """LangGraph-based conversational agent for AutoStream"""
    
    def __init__(self, llm):
        self.llm = llm
        self.intent_classifier = IntentClassifier(llm)
        self.rag = AutoStreamRAG()
        
        # KEY CHANGE: Pass LLM to LeadCollector for smart extraction
        self.lead_collector = LeadCollector(llm)
        
        # Build the graph
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("classify_intent", self.classify_intent_node)
        workflow.add_node("handle_greeting", self.handle_greeting_node)
        workflow.add_node("handle_inquiry", self.handle_inquiry_node)
        workflow.add_node("handle_high_intent", self.handle_high_intent_node)
        workflow.add_node("collect_lead_data", self.collect_lead_data_node)
        
        # Set entry point
        workflow.set_entry_point("classify_intent")
        
        # Add conditional edges from intent classification
        workflow.add_conditional_edges(
            "classify_intent",
            self.route_by_intent,
            {
                "greeting": "handle_greeting",
                "inquiry": "handle_inquiry",
                "high_intent": "handle_high_intent",
                "continue_collection": "collect_lead_data"
            }
        )
        
        # Add edges to END
        workflow.add_edge("handle_greeting", END)
        workflow.add_edge("handle_inquiry", END)
        workflow.add_edge("handle_high_intent", END)
        workflow.add_edge("collect_lead_data", END)
        
        return workflow
    
    def classify_intent_node(self, state: AgentState) -> AgentState:
        """Node: Classify user intent"""
        user_message = state["user_message"]
        
        # Check if we're in lead collection mode
        if state.get("awaiting_field"):
            # UX IMPROVEMENT: Allow user to exit flow
            exit_keywords = ["cancel", "stop", "never mind", "quit", "exit"]
            if any(w in user_message.lower() for w in exit_keywords):
                state["awaiting_field"] = None
                state["lead_data"] = {} # Clear partial data
                state["intent"] = "greeting" # Reset intent
                state["response"] = "No problem! I've cancelled that. Is there anything else I can help you with regarding AutoStream?"
                # Force route to greeting to handle the response generation or just return
                # In this architecture, we set intent to greeting but we already set response, 
                # so we might need a way to skip processing. 
                # For simplicity, we'll just return the state and let the router send it to greeting
                # which will overwrite the response. 
                # BETTER: Let's just handle it right here and trick the router.
                state["intent"] = "greeting" 
                return state

            # Continue with lead collection
            state["intent"] = "continue_collection"
            return state
        
        # Classify intent normally
        intent = self.intent_classifier.classify(
            user_message,
            conversation_history=state.get("messages", [])
        )
        state["intent"] = intent.value
        
        return state
    
    def route_by_intent(self, state: AgentState) -> Literal["greeting", "inquiry", "high_intent", "continue_collection"]:
        """Routing function based on intent"""
        intent = state["intent"]
        
        if intent == "continue_collection":
            return "continue_collection"
        elif intent == "greeting":
            return "greeting"
        elif intent == "inquiry":
            return "inquiry"
        else:  # high_intent
            return "high_intent"
    
    def handle_greeting_node(self, state: AgentState) -> AgentState:
        """Node: Handle casual greetings"""
        # If we just cancelled a flow, preserve the response we set in classify_intent
        if state.get("response") and "cancelled" in state["response"]:
            return state

        greeting_prompt = """You are a friendly AI assistant for AutoStream, an automated video editing SaaS.

Respond warmly to the user's greeting and briefly mention that you can help them with:
- Learning about AutoStream's pricing and features
- Finding the right plan for their content creation needs
- Getting started with a free trial

Keep it conversational and helpful. Don't be overly salesy.

User: {message}"""
        
        response = self.llm.invoke([
            HumanMessage(content=greeting_prompt.format(message=state["user_message"]))
        ])
        state["response"] = response.content
        
        return state
    
    def handle_inquiry_node(self, state: AgentState) -> AgentState:
        """Node: Handle product/pricing inquiries using RAG"""
        user_message = state["user_message"]
        
        # Retrieve relevant context
        lower_msg = user_message.lower()
        pricing_keywords = ["price", "pricing", "plan", "plans", "cost", "subscription"]
        k = 6 if any(w in lower_msg for w in pricing_keywords) else 3
        context = self.rag.get_context_for_query(user_message, k=k)
        state["rag_context"] = context
        
        # Generate response
        rag_prompt = """You are an expert sales assistant for AutoStream, an AI-powered video editing SaaS platform.

Use the following information from our knowledge base to answer the user's question accurately and helpfully:

KNOWLEDGE BASE:
{context}

Guidelines:
- Answer based ONLY on the provided knowledge base
- Be specific about pricing, features, and policies
- If the user asks about something not in the knowledge base, politely say you don't have that information
- Keep responses concise but complete
- Be friendly and professional

User Question: {question}

Your Answer:"""
        
        response = self.llm.invoke([
            HumanMessage(content=rag_prompt.format(
                context=context,
                question=user_message
            ))
        ])
        state["response"] = response.content
        
        return state
    
    def handle_high_intent_node(self, state: AgentState) -> AgentState:
        """Node: Detect high intent and start lead collection"""
        # Extract any info from initial message
        self.lead_collector.extract_from_message(state["user_message"])
        
        # Check next step
        next_question = self.lead_collector.get_next_question()
        
        if next_question:
            response = f"That's fantastic! I'd love to help you get started with AutoStream. {next_question}"
            state["awaiting_field"] = self.lead_collector.get_missing_fields()[0]
        else:
            # All info provided immediately
            result = self.lead_collector.capture_lead()
            state["lead_data"] = self.lead_collector.collected_data
            
            response = f"Perfect! Thank you, {self.lead_collector.collected_data['name']}! 🎉\n\n"
            response += "I've registered your interest in AutoStream and captured all your details. "
            response += f"Our team will reach out to {self.lead_collector.collected_data['email']} within 24 hours!"
        
        state["response"] = response
        
        return state
    
    def collect_lead_data_node(self, state: AgentState) -> AgentState:
        """Node: Collect lead information across multiple turns"""
        user_message = state["user_message"]
        current_field = state.get("awaiting_field")
        
        # Extract information using LLM
        self.lead_collector.extract_from_message(user_message, current_field)
        
        # Check completion
        if self.lead_collector.is_complete():
            result = self.lead_collector.capture_lead()
            state["lead_data"] = self.lead_collector.collected_data
            state["awaiting_field"] = None
            
            response = f"Perfect! Thank you, {self.lead_collector.collected_data['name']}! 🎉\n\n"
            response += "I've registered your interest in AutoStream. Our team will reach out to "
            response += f"{self.lead_collector.collected_data['email']} within 24 hours to help you "
            response += f"get started with optimizing your {self.lead_collector.collected_data['platform']} content!\n\n"
            response += "In the meantime, you can start your 14-day free trial at autostream.com/trial"
            
            state["response"] = response
        else:
            # Still need info
            next_question = self.lead_collector.get_next_question()
            state["awaiting_field"] = self.lead_collector.get_missing_fields()[0]
            state["response"] = next_question
        
        return state
    
    def run(self, user_message: str, current_state: dict = None) -> dict:
        """Run the agent with a user message"""
        # Initialize state
        if current_state is None:
            current_state = {
                "messages": [],
                "user_message": user_message,
                "intent": "",
                "rag_context": "",
                "lead_data": {},
                "awaiting_field": None,
                "response": "",
                "next_action": ""
            }
        else:
            current_state["messages"] = current_state.get("messages", []) + [user_message]
            current_state["user_message"] = user_message
        
        # Run the workflow
        result = self.app.invoke(current_state)
        
        # Add agent response to history
        if "response" in result:
            result["messages"] = result.get("messages", []) + [result["response"]]
        
        return result
    
    def reset(self):
        """Reset the lead collector"""
        self.lead_collector.reset()


if __name__ == "__main__":
    # Test the workflow
    from langchain_google_genai import ChatGoogleGenerativeAI
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    # Ensure you have GOOGLE_API_KEY in your .env
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)
    agent = AutoStreamAgent(llm)
    
    print("AutoStream Agent Test")
    print("=" * 60)
    
    test_conversation = [
        "Hi there!",
        "What are your pricing plans?",
        "That sounds good! I want to try the Pro plan for my YouTube channel",
        "Sarah Martinez",
        "sarah.martinez@email.com"
    ]
    
    state = None
    for message in test_conversation:
        print(f"\nUser: {message}")
        state = agent.run(message, state)
        print(f"Agent: {state['response']}")