import lancedb
import numpy as np
import logging
import time
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer

from ..config import settings

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    def __init__(self):
        # Initialize the sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # Lightweight model for embeddings
        self.db = None
        self.table = None
        
    def initialize_lancedb(self):
        """Initialize LanceDB connection and create/get table"""
        if self.db is None:
            self.db = lancedb.connect(settings.lancedb_path)
            
        # Get or create the embeddings table
        try:
            self.table = self.db.open_table("embeddings")
        except:
            # Create table if it doesn't exist
            schema = {
                "id": str,
                "vector": [float],  # Will be filled with actual embedding dimensions
                "text": str,
                "source_id": str,
                "created_at": float
            }
            # Create with a sample to infer schema
            sample_embedding = self.model.encode(["sample text"])[0].tolist()
            sample_data = [{
                "id": "sample",
                "vector": sample_embedding,
                "text": "sample text",
                "source_id": "sample",
                "created_at": time.time()
            }]
            self.table = self.db.create_table("embeddings", sample_data)
            
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a given text"""
        embedding = self.model.encode([text])[0]  # Get first (and only) embedding
        return embedding.tolist()
    
    def store_embedding(self, text_id: str, embedding: List[float], text: str, source_id: str) -> bool:
        """Store embedding in LanceDB"""
        if self.table is None:
            self.initialize_lancedb()
            
        try:
            data = [{
                "id": text_id,
                "vector": embedding,
                "text": text,
                "source_id": source_id,
                "created_at": time.time()
            }]
            self.table.add(data)
            return True
        except Exception as e:
            logger.error(f"Error storing embedding: {e}")
            return False
    
    def search_similar(self, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar embeddings"""
        if self.table is None:
            self.initialize_lancedb()
            
        try:
            query_embedding = self.generate_embedding(query_text)
            result = self.table.search(query_embedding).limit(limit).to_list()
            return result
        except Exception as e:
            logger.error(f"Error searching embeddings: {e}")
            return []

# Global instance
embedding_generator = EmbeddingGenerator()

def generate_and_store_embedding(text_id: str, text: str, source_id: str = None) -> Dict[str, Any]:
    """
    Generate embedding for text and store it in LanceDB
    """
    logger.info(f"Generating embedding for text ID: {text_id}")
    
    try:
        # Generate the embedding
        embedding = embedding_generator.generate_embedding(text)
        
        # Store in LanceDB
        success = embedding_generator.store_embedding(text_id, embedding, text, source_id or text_id)
        
        if success:
            result = {
                "embedding_id": text_id,
                "vector_length": len(embedding),
                "source_id": source_id or text_id,
                "timestamp": time.time()
            }
            logger.info(f"Successfully generated and stored embedding for: {text_id}")
            return result
        else:
            raise Exception("Failed to store embedding in LanceDB")
            
    except Exception as e:
        logger.error(f"Error in embedding generation: {str(e)}")
        raise e