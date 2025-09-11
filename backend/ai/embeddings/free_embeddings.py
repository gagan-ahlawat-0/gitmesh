"""
Free Open-Source Embedding Service for GitMesh AI
Uses Sentence Transformers for high-quality embeddings without API costs
"""

import os
import logging
from typing import List, Optional, Union
import numpy as np

logger = logging.getLogger(__name__)

class GitMeshEmbeddings:
    """
    Free, open-source embedding service using Sentence Transformers.
    Provides production-quality embeddings without API costs.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_folder: Optional[str] = None):
        """
        Initialize the embedding service.
        
        Args:
            model_name: HuggingFace model name. Recommended options:
                - "all-MiniLM-L6-v2": Fast, good quality, 384 dimensions
                - "all-mpnet-base-v2": Best quality, 768 dimensions, slower
                - "paraphrase-MiniLM-L3-v2": Very fast, 384 dimensions
            cache_folder: Directory to cache models (default: ~/.cache/huggingface)
        """
        self.model_name = model_name
        self.cache_folder = cache_folder or os.path.expanduser("~/.cache/huggingface")
        self._model = None
        self._embedding_dim = None
        
        # Ensure cache directory exists
        os.makedirs(self.cache_folder, exist_ok=True)
        
    @property
    def model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(
                    self.model_name, 
                    cache_folder=self.cache_folder
                )
                # Get embedding dimension
                test_embedding = self._model.encode("test")
                self._embedding_dim = len(test_embedding)
                logger.info(f"Model loaded successfully. Embedding dimension: {self._embedding_dim}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
        return self._model
    
    @property 
    def embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model."""
        if self._embedding_dim is None:
            # Force model loading to get dimension
            _ = self.model
        return self._embedding_dim
    
    def embed(self, texts: Union[str, List[str]], normalize: bool = True) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Generate embeddings for text(s).
        
        Args:
            texts: Single text string or list of texts
            normalize: Whether to normalize embeddings (recommended for cosine similarity)
            
        Returns:
            Embedding(s) as numpy array(s)
        """
        try:
            # Handle single text input
            is_single = isinstance(texts, str)
            if is_single:
                texts = [texts]
            
            # Generate embeddings
            embeddings = self.model.encode(
                texts, 
                normalize_embeddings=normalize,
                show_progress_bar=len(texts) > 10  # Show progress for large batches
            )
            
            # Return single embedding for single input
            if is_single:
                return embeddings[0]
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def embed_batch(self, texts: List[str], batch_size: int = 32, normalize: bool = True) -> List[np.ndarray]:
        """
        Generate embeddings for large batches of texts efficiently.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            normalize: Whether to normalize embeddings
            
        Returns:
            List of embeddings
        """
        try:
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = self.embed(batch_texts, normalize=normalize)
                all_embeddings.extend(batch_embeddings)
                
                if len(texts) > 100:  # Log progress for large datasets
                    logger.info(f"Processed {min(i + batch_size, len(texts))}/{len(texts)} texts")
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Cosine similarity score (-1 to 1)
        """
        try:
            # Ensure embeddings are normalized
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return np.dot(embedding1, embedding2) / (norm1 * norm2)
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def find_most_similar(self, query_embedding: np.ndarray, candidate_embeddings: List[np.ndarray], 
                         top_k: int = 5) -> List[tuple]:
        """
        Find most similar embeddings to a query embedding.
        
        Args:
            query_embedding: Query embedding to search for
            candidate_embeddings: List of candidate embeddings
            top_k: Number of most similar results to return
            
        Returns:
            List of (index, similarity_score) tuples, sorted by similarity
        """
        try:
            similarities = []
            
            for i, candidate in enumerate(candidate_embeddings):
                sim_score = self.similarity(query_embedding, candidate)
                similarities.append((i, sim_score))
            
            # Sort by similarity (descending) and return top_k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Failed to find similar embeddings: {e}")
            return []

# Factory function for different embedding models
def get_embedding_service(model_type: str = "fast") -> GitMeshEmbeddings:
    """
    Get an embedding service with predefined configurations.
    
    Args:
        model_type: Type of model to use:
            - "fast": Fast inference, good quality (all-MiniLM-L6-v2)
            - "best": Best quality, slower inference (all-mpnet-base-v2)  
            - "tiny": Fastest inference, lower quality (paraphrase-MiniLM-L3-v2)
            
    Returns:
        Configured GitMeshEmbeddings instance
    """
    model_configs = {
        "fast": "all-MiniLM-L6-v2",  # 22MB, 384 dim, good balance
        "best": "all-mpnet-base-v2",  # 420MB, 768 dim, best quality
        "tiny": "paraphrase-MiniLM-L3-v2",  # 17MB, 384 dim, very fast
    }
    
    model_name = model_configs.get(model_type, model_configs["fast"])
    logger.info(f"Initializing {model_type} embedding service with model: {model_name}")
    
    return GitMeshEmbeddings(model_name=model_name)

# Singleton instance for the default embedding service
_default_embeddings = None

def get_default_embeddings() -> GitMeshEmbeddings:
    """Get the default embedding service (singleton pattern)."""
    global _default_embeddings
    if _default_embeddings is None:
        _default_embeddings = get_embedding_service("fast")
    return _default_embeddings
