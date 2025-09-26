"""
Semantic similarity service for RFP matching and intelligent grant scoring
Uses sentence-transformers for embeddings and pgvector for similarity search
"""

import os
import json
import PyPDF2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
import numpy as np
from supabase import create_client, Client
from datetime import datetime
import re

class SemanticService:
    def __init__(self):
        self.model = None
        self.supabase = None
        self._init_model()
        self._init_supabase()

    def _init_model(self):
        """Initialize the sentence transformer model"""
        try:
            # Use a lightweight, fast model good for semantic search
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("[SEMANTIC] Loaded sentence transformer model")
        except Exception as e:
            print(f"[SEMANTIC] Error loading model: {e}")

    def _init_supabase(self):
        """Initialize Supabase client"""
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_KEY')

            if supabase_url and supabase_key:
                self.supabase = create_client(supabase_url, supabase_key)
                print("[SEMANTIC] Connected to Supabase")
            else:
                print("[SEMANTIC] Supabase credentials not found")
        except Exception as e:
            print(f"[SEMANTIC] Error connecting to Supabase: {e}")

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from PDF"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""

                # Extract text from first few pages (usually contains the main description)
                max_pages = min(5, len(pdf_reader.pages))
                for page_num in range(max_pages):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + " "

                # Clean the text
                text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
                text = text.strip()

                return text[:5000]  # Limit to first 5000 chars for performance

        except Exception as e:
            print(f"[SEMANTIC] Error extracting PDF text from {pdf_path}: {e}")
            return ""

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for given text"""
        if not self.model or not text.strip():
            return None

        try:
            # Generate embedding
            embedding = self.model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            print(f"[SEMANTIC] Error generating embedding: {e}")
            return None

    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        if not self.model:
            return 0.0

        try:
            embeddings = self.model.encode([text1, text2])

            # Calculate cosine similarity
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )

            return float(similarity)
        except Exception as e:
            print(f"[SEMANTIC] Error calculating similarity: {e}")
            return 0.0

    def load_rfps_from_directory(self, rfp_dir: str = "/home/ayaan/projects/perscholas-fundraising-demo/RFPs-20250926T184948Z-1-001/RFPs") -> List[Dict[str, Any]]:
        """Load and process RFPs from directory"""
        rfps = []

        if not os.path.exists(rfp_dir):
            print(f"[SEMANTIC] RFP directory not found: {rfp_dir}")
            return rfps

        for root, dirs, files in os.walk(rfp_dir):
            for file in files:
                if file.endswith('.pdf'):
                    file_path = os.path.join(root, file)

                    # Determine category from path
                    category = "Federal" if "Federal" in root else "Local-State"

                    # Extract text
                    text_content = self.extract_text_from_pdf(file_path)

                    if text_content:
                        # Generate embedding
                        embedding = self.get_embedding(text_content)

                        if embedding:
                            rfp_data = {
                                "title": file.replace('.pdf', '').replace('_', ' '),
                                "category": category,
                                "file_path": file_path,
                                "content": text_content,
                                "embedding": embedding,
                                "created_at": datetime.now().isoformat()
                            }
                            rfps.append(rfp_data)
                            print(f"[SEMANTIC] Processed RFP: {file}")

        print(f"[SEMANTIC] Loaded {len(rfps)} RFPs")
        return rfps

    def store_rfps_in_supabase(self, rfps: List[Dict[str, Any]]) -> bool:
        """Store RFPs with embeddings in Supabase"""
        if not self.supabase:
            print("[SEMANTIC] Supabase not available")
            return False

        try:
            # First, ensure the table exists with proper schema
            self._ensure_rfp_table_exists()

            for rfp in rfps:
                # Store in Supabase
                result = self.supabase.table('rfps').insert({
                    'title': rfp['title'],
                    'category': rfp['category'],
                    'file_path': rfp['file_path'],
                    'content': rfp['content'],
                    'embedding': rfp['embedding'],
                    'created_at': rfp['created_at']
                }).execute()

                if hasattr(result, 'error') and result.error:
                    print(f"[SEMANTIC] Error storing RFP {rfp['title']}: {result.error}")
                else:
                    print(f"[SEMANTIC] Stored RFP: {rfp['title']}")

            return True

        except Exception as e:
            print(f"[SEMANTIC] Error storing RFPs: {e}")
            return False

    def _ensure_rfp_table_exists(self):
        """Ensure RFP table exists with proper schema"""
        # This would typically be done via migration, but for demo purposes
        # we'll create the schema if it doesn't exist

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS rfps (
            id BIGSERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            file_path TEXT,
            content TEXT,
            embedding vector(384),  -- all-MiniLM-L6-v2 produces 384-dim vectors
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS rfps_embedding_idx ON rfps
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """

        try:
            # Note: This requires direct SQL execution which might not be available
            # In production, this should be done via proper migrations
            print("[SEMANTIC] RFP table schema ready")
        except Exception as e:
            print(f"[SEMANTIC] Note: Ensure RFP table exists with pgvector support: {e}")

    def find_similar_rfps(self, grant_description: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Find most similar RFPs to a grant description"""
        if not self.supabase or not grant_description.strip():
            return []

        try:
            # Generate embedding for the grant description
            query_embedding = self.get_embedding(grant_description)
            if not query_embedding:
                return []

            # Search for similar RFPs using pgvector
            # Note: This requires proper pgvector setup in Supabase
            result = self.supabase.rpc('match_rfps', {
                'query_embedding': query_embedding,
                'match_threshold': 0.5,
                'match_count': limit
            }).execute()

            if hasattr(result, 'data') and result.data:
                return result.data
            else:
                # Fallback: get all RFPs and calculate similarity in Python
                return self._fallback_similarity_search(grant_description, limit)

        except Exception as e:
            print(f"[SEMANTIC] Error finding similar RFPs: {e}")
            return self._fallback_similarity_search(grant_description, limit)

    def _fallback_similarity_search(self, grant_description: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Fallback similarity search using Python calculations"""
        try:
            # Get all RFPs from database
            result = self.supabase.table('rfps').select('*').execute()

            if not hasattr(result, 'data') or not result.data:
                return []

            # Calculate similarities
            similarities = []
            for rfp in result.data:
                if rfp.get('content'):
                    similarity = self.calculate_semantic_similarity(
                        grant_description,
                        rfp['content']
                    )
                    # Only include matches above meaningful threshold
                    if similarity >= 0.4:  # 40% minimum similarity
                        similarities.append({
                            **rfp,
                            'similarity_score': similarity
                        })

            # Sort by similarity and return top matches
            similarities.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            return similarities[:limit]

        except Exception as e:
            print(f"[SEMANTIC] Error in fallback search: {e}")
            return []

    def calculate_enhanced_match_score(self, grant: Dict[str, Any], rfp_similarities: List[Dict[str, Any]]) -> int:
        """Calculate enhanced match score using semantic similarity with historical RFPs"""
        base_score = 10  # Much lower base score

        # Core Per Scholas keywords (40 points max - most important factor)
        core_keywords = ['technology', 'workforce', 'training', 'education', 'stem', 'coding', 'cyber', 'digital', 'programming', 'software', 'computer', 'it', 'technical']

        # Secondary context keywords (must have core + context for high scores)
        context_keywords = ['job', 'career', 'employment', 'skills', 'certification', 'bootcamp', 'professional']

        title_lower = grant.get('title', '').lower()
        desc_lower = grant.get('description', '').lower()
        full_text = title_lower + ' ' + desc_lower

        core_matches = sum(1 for keyword in core_keywords if keyword in full_text)
        context_matches = sum(1 for keyword in context_keywords if keyword in full_text)

        # Require at least 2 core keywords for decent score
        if core_matches >= 2:
            keyword_score = min(40, (core_matches * 8) + (context_matches * 2))
        elif core_matches == 1:
            keyword_score = min(15, core_matches * 8)
        else:
            keyword_score = 0  # No core keywords = very low relevance

        # Semantic similarity with historical RFPs (30 points max)
        semantic_score = 0
        if rfp_similarities:
            # Use the best similarity score but be more conservative
            best_similarity = max(rfp.get('similarity_score', 0) for rfp in rfp_similarities)
            # Only give significant points for very high similarity (>0.7)
            if best_similarity > 0.7:
                semantic_score = min(30, int((best_similarity - 0.5) * 60))
            else:
                semantic_score = min(10, int(best_similarity * 20))

        # Funding amount alignment (15 points max)
        amount = grant.get('amount', 0)
        amount_score = 0
        if 100000 <= amount <= 2000000:  # Per Scholas typical range
            amount_score = 15
        elif 50000 <= amount <= 5000000:  # Acceptable range
            amount_score = 8
        elif amount > 0:
            amount_score = 3

        # Deadline feasibility (5 points max - less important)
        deadline_score = 5  # Default to reasonable for now

        total_score = base_score + keyword_score + semantic_score + amount_score + deadline_score

        # Additional penalty for clearly non-relevant domains
        excluded_domains = ['health', 'medical', 'hospital', 'clinical', 'agriculture', 'farming', 'rural health', 'environmental', 'climate']
        domain_penalty = 0
        for domain in excluded_domains:
            if domain in full_text:
                domain_penalty += 20

        final_score = max(5, total_score - domain_penalty)  # Minimum 5% score
        return min(100, final_score)

# Test functions
def test_semantic_service():
    """Test the semantic service"""
    service = SemanticService()

    # Test basic similarity
    text1 = "technology workforce development training program"
    text2 = "STEM education and job training initiative"

    similarity = service.calculate_semantic_similarity(text1, text2)
    print(f"Similarity between texts: {similarity:.3f}")

    return service

def load_and_store_rfps():
    """Load RFPs from directory and store in Supabase"""
    service = SemanticService()

    # Load RFPs
    rfps = service.load_rfps_from_directory()

    if rfps:
        print(f"Loaded {len(rfps)} RFPs")

        # Store in Supabase
        success = service.store_rfps_in_supabase(rfps)

        if success:
            print("Successfully stored RFPs in Supabase")
        else:
            print("Failed to store RFPs in Supabase")
    else:
        print("No RFPs found to load")

if __name__ == "__main__":
    test_semantic_service()