import pytest
import pytest

def test_torch_available():
    """Test that torch is available."""
    try:
        import torch
        assert torch.__version__ is not None
    except ImportError:
        pytest.skip("torch not installed")

def test_cuda_if_available():
    """Test CUDA availability (informational)."""
    try:
        import torch
        if torch.cuda.is_available():
            print(f"CUDA Available: {torch.version.cuda}")
            print(f"Device: {torch.cuda.get_device_name(0)}")
            assert True
        else:
            print("CUDA not available (running on CPU)")
    except ImportError:
        pytest.skip("torch not installed")

def test_sentence_transformer_loading():
    """Test loading the embedding model."""
    try:
        from sentence_transformers import SentenceTransformer
        import torch
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
        
        # Test encoding
        embedding = model.encode("test sentence")
        assert len(embedding) > 0
        assert model.get_sentence_embedding_dimension() == len(embedding)
        
    except ImportError:
        pytest.skip("sentence-transformers or torch not installed")
    except Exception as e:
        pytest.fail(f"Failed to load sentence transformer: {e}")
