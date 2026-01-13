"""
Lead Capture Tool for AutoStream Agent
Handles data collection using LLM-based extraction
"""

import json
import re
from typing import Optional, Dict, List
from langchain_core.messages import HumanMessage, SystemMessage

def mock_lead_capture(name: str, email: str, platform: str) -> Dict[str, str]:
    """
    Mock API function to capture lead information
    """
    print(f"\n{'='*60}")
    print(f"LEAD CAPTURED SUCCESSFULLY!")
    print(f"{'='*60}")
    print(f"Name: {name}")
    print(f"Email: {email}")
    print(f"Platform: {platform}")
    print(f"{'='*60}\n")
    
    return {
        "status": "success",
        "message": f"Lead captured successfully: {name}, {email}, {platform}",
        "lead_id": f"LEAD_{hash(email) % 10000:04d}"
    }


class LeadCollector:
    """Manages multi-turn lead data collection using LLM extraction"""
    
    REQUIRED_FIELDS = ["name", "email", "platform"]
    
    def __init__(self, llm=None):
        """
        Initialize the collector.
        Args:
            llm: The LLM instance to use for smart extraction.
        """
        self.llm = llm
        self.collected_data: Dict[str, Optional[str]] = {
            "name": None,
            "email": None,
            "platform": None
        }
        
        self.extraction_system_prompt = """
        You are a data extraction assistant. Extract the following fields from the user's message:
        - name (Person's name)
        - email (Email address)
        - platform (Content platform e.g., YouTube, Instagram, TikTok)

        Rules:
        1. Only extract information explicitly stated.
        2. If the user mentions a platform in a negative context (e.g., "I don't use TikTok"), DO NOT extract it.
        3. If the user corrects previous info, extract the new value.
        4. Return NULL for missing fields.
        
        Respond ONLY with a valid JSON object:
        {
            "name": "extracted name or null",
            "email": "extracted email or null",
            "platform": "extracted platform or null"
        }
        """
    
    def extract_from_message(self, message: str, field_hint: Optional[str] = None) -> bool:
        """
        Extract information from user message using LLM
        """
        # If no LLM provided, fall back to simple keyword matching (Safety fallback)
        if not self.llm:
            return self._manual_extract(message, field_hint)

        try:
            # Prompt the LLM
            response = self.llm.invoke([
                SystemMessage(content=self.extraction_system_prompt),
                HumanMessage(content=f"Current known data: {self.collected_data}\nUser message: {message}")
            ])
            
            # Clean and Parse JSON
            content = response.content.strip()
            # Extract JSON block if wrapped in markdown
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            
            if json_match:
                extracted = json.loads(json_match.group())
                
                updated = False
                for field in self.REQUIRED_FIELDS:
                    # Only update if the LLM found a new value (not null) and it's not the string "null"
                    val = extracted.get(field)
                    if val and val != "null" and str(val).lower() != "none":
                        # If we already have data, only overwrite if it looks like a correction
                        if self.collected_data[field] != val:
                            self.collected_data[field] = val
                            updated = True
                return updated
            
        except Exception as e:
            print(f"Extraction error: {e}. Falling back to manual extraction.")
            return self._manual_extract(message, field_hint)
            
        return False

    def _manual_extract(self, message: str, field_hint: str) -> bool:
        """Fallback manual extraction logic (simplified from original)"""
        updated = False
        msg_lower = message.lower()
        
        # Simple Email
        if "@" in message and "." in message:
            for word in message.split():
                if "@" in word:
                    self.collected_data["email"] = word.strip(".,!?")
                    updated = True
        
        # Simple Platform
        platforms = ["YouTube", "Instagram", "TikTok", "LinkedIn", "Twitter", "Twitch"]
        for p in platforms:
            if p.lower() in msg_lower:
                self.collected_data["platform"] = p
                updated = True
                
        # Simple Name (only if hinting)
        if field_hint == "name" and not updated:
            name_candidate = message.strip().title()
            if len(name_candidate.split()) <= 3:
                self.collected_data["name"] = name_candidate
                updated = True
                
        return updated

    def get_missing_fields(self) -> list:
        """Get list of fields still needed"""
        return [field for field, value in self.collected_data.items() if value is None]
    
    def is_complete(self) -> bool:
        """Check if all required fields are collected"""
        return all(self.collected_data[field] is not None for field in self.REQUIRED_FIELDS)
    
    def get_next_question(self) -> Optional[str]:
        """Get the next question to ask based on missing fields"""
        missing = self.get_missing_fields()
        if not missing:
            return None
        
        next_field = missing[0]
        questions = {
            "name": "Great! What's your name?",
            "email": "Perfect! What's your email address?",
            "platform": "Awesome! Which platform do you create content for? (YouTube, Instagram, TikTok, etc.)"
        }
        return questions.get(next_field)
    
    def capture_lead(self) -> Dict[str, str]:
        """Execute lead capture"""
        if not self.is_complete():
            raise ValueError("Incomplete data")
            
        return mock_lead_capture(**self.collected_data)

    def reset(self):
        """Reset data"""
        self.collected_data = {k: None for k in self.collected_data}