import pytest
from memory_system import LongTermMemory, MemoryEntry
from config import Config
import shutil

@pytest.fixture(scope="module")
def memory_system():
    """Fixture to provide a memory system instance."""
    # Ensure config dirs exist
    Config.ensure_directories()
    
    # Create instance
    memory = LongTermMemory()
    return memory

def test_store_and_recall_experience(memory_system):
    """Test storing and recalling an experience."""
    experience = {
        "command": "test_cmd",
        "result": "success",
        "context": "testing context"
    }
    
    # Store
    memory_system.store_experience(experience, category="experience")
    
    # Recall
    # Note: Vector search might be fuzzy, but for exact string it should find it
    results = memory_system.recall_similar("test_cmd", category="experience", limit=1)
    
    assert len(results) > 0
    assert "test_cmd" in results[0]['content']

def test_memory_categories(memory_system):
    """Test that different categories work."""
    # Fact
    memory_system.store_fact("The sky is blue", source="observation")
    # Procedure
    memory_system.store_procedure("make_coffee", ["boil water", "add beans"], success_rate=0.9)
    
    stats = memory_system.get_statistics()
    assert stats['facts'] > 0
    assert stats['procedures'] > 0

def test_error_solutions(memory_system):
    """Test storing and retrieving error solutions."""
    error_data = {
        "error": "Permission denied",
        "solution": "chmod +x file",
        "command": "./script.sh"
    }
    
    memory_system.store_experience(error_data, category="error")
    
    solutions = memory_system.get_error_solutions("Permission denied")
    assert len(solutions) > 0
