"""
RAG Pipeline for AutoStream Knowledge Base
Handles document loading, vector storage, and retrieval
"""

import json
import os
from typing import List, Dict
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings


class AutoStreamRAG:
    """RAG pipeline for retrieving AutoStream product knowledge"""
    
    def __init__(self, knowledge_filename: str = "autostream_knowledge.json"):
        # ROBUST PATH HANDLING:
        # Get the absolute path to the project root (3 levels up from this file)
        # src/utils/rag_pipeline.py -> src/utils -> src -> PROJECT_ROOT
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Construct absolute paths
        self.knowledge_path = os.path.join(self.project_root, "data", knowledge_filename)
        self.persist_directory = os.path.join(self.project_root, "chroma_db")
        
        # Initialize Embeddings (using a local lightweight model)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        self.vector_store = None
        self._initialize_vector_store()
    
    def _load_knowledge_base(self) -> List[Document]:
        """Load and parse the knowledge base JSON file"""
        # check if file exists
        if not os.path.exists(self.knowledge_path):
            raise FileNotFoundError(f"Knowledge base not found at {self.knowledge_path}")

        with open(self.knowledge_path, 'r') as f:
            data = json.load(f)
        
        documents = []
        
        # 1. Company info
        company = data.get('company', {})
        doc_text = f"Company: {company.get('name')}\n"
        doc_text += f"Description: {company.get('description')}\n"
        doc_text += f"Mission: {company.get('mission')}"
        documents.append(Document(
            page_content=doc_text,
            metadata={"type": "company_info"}
        ))
        
        # 2. Pricing plans
        for plan in data.get('pricing', {}).get('plans', []):
            doc_text = f"Plan: {plan['name']}\n"
            doc_text += f"Price: {plan['price']}\n"
            doc_text += f"Best for: {plan['best_for']}\n"
            doc_text += "Features:\n"
            doc_text += "\n".join([f"- {feature}" for feature in plan['features']])
            documents.append(Document(
                page_content=doc_text,
                metadata={"type": "pricing", "plan": plan['name']}
            ))
        
        # 3. Policies
        policies = data.get('policies', {})
        for policy_name, policy_text in policies.items():
            if isinstance(policy_text, dict):
                # Handle nested policies like support
                for sub_key, sub_value in policy_text.items():
                    doc_text = f"Policy: {policy_name} - {sub_key}\n{sub_value}"
                    documents.append(Document(
                        page_content=doc_text,
                        metadata={"type": "policy", "category": policy_name}
                    ))
            else:
                doc_text = f"Policy: {policy_name}\n{policy_text}"
                documents.append(Document(
                    page_content=doc_text,
                    metadata={"type": "policy", "category": policy_name}
                ))
        
        # 4. Features
        features = data.get('features', {})
        for feature_name, feature_desc in features.items():
            doc_text = f"Feature: {feature_name}\n{feature_desc}"
            documents.append(Document(
                page_content=doc_text,
                metadata={"type": "feature", "feature_name": feature_name}
            ))
        
        # 5. FAQ
        for faq in data.get('faq', []):
            doc_text = f"Question: {faq['question']}\nAnswer: {faq['answer']}"
            documents.append(Document(
                page_content=doc_text,
                metadata={"type": "faq"}
            ))
        
        # 6. Supported platforms
        platforms = data.get('platforms_supported', [])
        doc_text = "Supported Platforms:\n" + ", ".join(platforms)
        documents.append(Document(
            page_content=doc_text,
            metadata={"type": "platforms"}
        ))
        
        return documents
    
    def _initialize_vector_store(self):
        """
        Initialize ChromaDB vector store.
        OPTIMIZATION: Checks if DB exists to avoid re-embedding on every run.
        """
        # Check if DB already exists and has content
        if os.path.exists(self.persist_directory) and os.listdir(self.persist_directory):
            print(f"Loading existing vector store from {self.persist_directory}...")
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
        else:
            print(f"Creating new vector store at {self.persist_directory}...")
            documents = self._load_knowledge_base()
            
            # Split documents
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50
            )
            split_docs = text_splitter.split_documents(documents)
            
            # Create and persist vector store
            self.vector_store = Chroma.from_documents(
                documents=split_docs,
                embedding=self.embeddings,
                persist_directory=self.persist_directory
            )
            print(f"Vector store created with {len(split_docs)} chunks.")
    
    def retrieve(self, query: str, k: int = 3) -> List[Document]:
        """Retrieve relevant documents for a query"""
        if not self.vector_store:
            raise ValueError("Vector store not initialized")
        
        results = self.vector_store.similarity_search(query, k=k)
        return results
    
    def get_context_for_query(self, query: str, k: int = 3) -> str:
        """Get formatted context string for a query"""
        docs = self.retrieve(query, k=k)
        context_parts = []
        
        for doc in docs:
            context_parts.append(doc.page_content)
        
        return "\n\n".join(context_parts)


if __name__ == "__main__":
    # Test the RAG pipeline
    try:
        rag = AutoStreamRAG()
        
        test_queries = [
            "What are your pricing plans?",
            "What's included in the Pro plan?",
            "What's your refund policy?",
            "Do you support YouTube?"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            print("=" * 50)
            context = rag.get_context_for_query(query)
            print(context)
            print()
            
    except Exception as e:
        print(f"Error initializing RAG: {e}")
        print("Ensure 'data/autostream_knowledge.json' exists.")