"""
Long-term memory system with vector database for semantic search.
Stores experiences, facts, procedures, and errors for future retrieval.
"""
import uuid
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import chromadb
from chromadb.config import Settings
from config import Config
from utils.embeddings import get_embedding_generator
from utils.logger import logger


@dataclass
class MemoryEntry:
    """A single memory entry in the long-term memory system."""
    id: str
    timestamp: str
    category: str  # "experience", "fact", "procedure", "error"
    content: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return asdict(self)


class LongTermMemory:
    """
    Long-term memory system with semantic search capabilities.
    Uses ChromaDB for vector storage and retrieval.
    """
    
    def __init__(self):
        """Initialize the long-term memory system."""
        self.embedding_generator = get_embedding_generator()
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(Config.VECTOR_DB_DIR),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create collections for different memory types
        self.experiences = self._get_or_create_collection("experiences")
        self.facts = self._get_or_create_collection("facts")
        self.procedures = self._get_or_create_collection("procedures")
        self.errors = self._get_or_create_collection("errors")
        
        logger.log_debug("Long-term memory system initialized")
    
    def _get_or_create_collection(self, name: str):
        """Get or create a ChromaDB collection."""
        return self.client.get_or_create_collection(
            name=name,
            metadata={"description": f"Storage for {name}"}
        )
    
    def store_experience(self, experience: Dict, category: str = "experience"):
        """
        Store an experience in long-term memory.
        
        Args:
            experience: Dict with command, result, context
            category: Memory category (experience, fact, procedure, error)
        """
        entry_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Create content string for embedding
        content = self._format_experience(experience)
        
        # Generate embedding
        embedding = self.embedding_generator.generate(content)
        
        # Select collection based on category
        collection = self._get_collection_by_category(category)
        
        # Store in ChromaDB
        collection.add(
            ids=[entry_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "timestamp": timestamp,
                "category": category,
                **experience
            }]
        )
        
        logger.log_memory_operation(
            "store",
            f"{category}: {content[:100]}..."
        )
    
    def recall_similar(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Retrieve similar memories using semantic search.
        
        Args:
            query: Query text to find similar memories
            category: Optional category filter
            limit: Maximum number of results
            
        Returns:
            List of similar memory entries
        """
        # Generate query embedding
        query_embedding = self.embedding_generator.generate(query)
        
        # Search in appropriate collections
        collections = (
            [self._get_collection_by_category(category)]
            if category
            else [self.experiences, self.facts, self.procedures, self.errors]
        )
        
        all_results = []
        
        for collection in collections:
            try:
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                )
                
                if results and results['ids'] and results['ids'][0]:
                    for i in range(len(results['ids'][0])):
                        all_results.append({
                            "id": results['ids'][0][i],
                            "content": results['documents'][0][i],
                            "metadata": results['metadatas'][0][i],
                            "distance": results['distances'][0][i] if 'distances' in results else None,
                        })
            except Exception as e:
                logger.log_error(e, f"Error querying collection {collection.name}")
        
        # Sort by distance and return top results
        all_results.sort(key=lambda x: x.get('distance', float('inf')))
        return all_results[:limit]
    
    def store_fact(self, fact: str, source: str):
        """
        Store a learned fact.
        
        Args:
            fact: The fact to store
            source: How this fact was discovered
        """
        self.store_experience(
            {
                "fact": fact,
                "source": source,
            },
            category="fact"
        )
    
    def store_procedure(
        self,
        name: str,
        steps: List[str],
        success_rate: float = 1.0,
        tags: List[str] = None
    ):
        """
        Store a successful procedure.
        
        Args:
            name: Name of the procedure
            steps: List of steps in the procedure
            success_rate: Success rate (0.0 to 1.0)
            tags: Optional tags for categorization
        """
        self.store_experience(
            {
                "procedure_name": name,
                "steps": json.dumps(steps),
                "success_rate": str(success_rate),
                "tags": json.dumps(tags or []),
            },
            category="procedure"
        )
    
    def get_error_solutions(self, error_text: str) -> List[Dict]:
        """
        Find solutions to similar errors from the past.
        
        Args:
            error_text: The error message or description
            
        Returns:
            List of past error solutions
        """
        return self.recall_similar(error_text, category="error", limit=3)
    
    def summarize_session(self, session_data: Dict) -> str:
        """
        Create a summary of the current session.
        
        Args:
            session_data: Data about the current session
            
        Returns:
            Summary string
        """
        summary_file = Config.SUMMARIES_DIR / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(summary_file, 'w') as f:
            json.dump(session_data, f, indent=2, default=str)
        
        logger.log_memory_operation("summarize", f"Session saved to {summary_file.name}")
        return str(summary_file)
    
    def get_statistics(self) -> Dict:
        """Get statistics about stored memories."""
        return {
            "experiences": self.experiences.count(),
            "facts": self.facts.count(),
            "procedures": self.procedures.count(),
            "errors": self.errors.count(),
            "total": sum([
                self.experiences.count(),
                self.facts.count(),
                self.procedures.count(),
                self.errors.count(),
            ])
        }
    
    def _get_collection_by_category(self, category: str):
        """Get the appropriate collection for a category."""
        collections = {
            "experience": self.experiences,
            "fact": self.facts,
            "procedure": self.procedures,
            "error": self.errors,
        }
        return collections.get(category, self.experiences)
    
    def _format_experience(self, experience: Dict) -> str:
        """Format an experience dict as a searchable string."""
        parts = []
        for key, value in experience.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            parts.append(f"{key}: {value}")
        return " | ".join(parts)
