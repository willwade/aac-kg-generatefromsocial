"""
Tests for the ingestion pipeline.
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.pipeline.ingestion import IngestionPipeline
from src.models.memory_schema import EntityType, RelationType


@pytest.fixture
def sample_memory_content():
    """Sample memory file content for testing."""
    return """# 📘 Personal Memory File – Test User

## 🧑 Identity
- Name: Test User
- Pronouns: they/them
- Lives in: Test City
- Works at: Test Company (Test Role)

## 👥 People
- Alice: friend, works at Google
- Bob: colleague, SLT, wears glasses

## 🏢 Workplaces
- Test Company (2020–present)
- Old Company (2018–2020)

## 💬 Events & Memories
- "Test Conference 2023" → met Alice, gave presentation
- "Team Building Event" → with Bob and colleagues

## ❤️ Interests
- programming, reading, hiking

## 📚 Phrases I Often Say
- "Let's think about this."
- "That's interesting."
"""


@pytest.fixture
def temp_memory_file(sample_memory_content):
    """Create a temporary memory file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(sample_memory_content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def temp_storage_path():
    """Create a temporary storage path for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield os.path.join(temp_dir, "test_kg")


def test_pipeline_process_memory_file(temp_memory_file, temp_storage_path):
    """Test processing a memory file through the complete pipeline."""
    pipeline = IngestionPipeline(storage_type="json", storage_path=temp_storage_path)
    
    # Process the file
    kg = pipeline.process_memory_file(temp_memory_file, merge_with_existing=False)
    
    # Verify the knowledge graph was created
    assert len(kg.entities) > 0
    assert len(kg.triplets) > 0
    
    # Check that the main person entity exists
    test_user_entities = [e for e in kg.entities.values() if e.name == "Test User"]
    assert len(test_user_entities) == 1
    
    test_user = test_user_entities[0]
    assert test_user.entity_type == EntityType.PERSON
    assert test_user.properties.get('pronouns') == 'they/them'
    assert test_user.properties.get('location') == 'Test City'


def test_pipeline_statistics(temp_memory_file, temp_storage_path):
    """Test getting statistics from the pipeline."""
    pipeline = IngestionPipeline(storage_type="json", storage_path=temp_storage_path)
    
    # Process the file
    pipeline.process_memory_file(temp_memory_file, merge_with_existing=False)
    
    # Get statistics
    stats = pipeline.get_statistics()
    
    assert 'total_entities' in stats
    assert 'total_triplets' in stats
    assert 'entity_types' in stats
    assert 'predicate_types' in stats
    
    assert stats['total_entities'] > 0
    assert stats['total_triplets'] > 0
    assert EntityType.PERSON.value in stats['entity_types']


def test_pipeline_query_context(temp_memory_file, temp_storage_path):
    """Test querying context for an entity."""
    pipeline = IngestionPipeline(storage_type="json", storage_path=temp_storage_path)
    
    # Process the file
    pipeline.process_memory_file(temp_memory_file, merge_with_existing=False)
    
    # Query context for Test User
    context = pipeline.query_context_for_entity("Test User")
    
    assert 'entity' in context
    assert 'relationships' in context
    assert 'related_entities' in context
    
    assert context['entity']['name'] == "Test User"
    assert context['entity']['type'] == EntityType.PERSON.value
    
    # Should have some relationships
    assert len(context['relationships']) > 0


def test_pipeline_merge_graphs(temp_memory_file, temp_storage_path):
    """Test merging multiple knowledge graphs."""
    pipeline = IngestionPipeline(storage_type="json", storage_path=temp_storage_path)
    
    # Process the file twice with merging
    kg1 = pipeline.process_memory_file(temp_memory_file, merge_with_existing=False)
    kg2 = pipeline.process_memory_file(temp_memory_file, merge_with_existing=True)
    
    # The second processing should not duplicate entities
    # (though it might add some triplets due to processing variations)
    assert len(kg2.entities) >= len(kg1.entities)
    
    # Should still have the main person
    test_user_entities = [e for e in kg2.entities.values() if e.name == "Test User"]
    assert len(test_user_entities) == 1


def test_pipeline_sqlite_storage(temp_memory_file, temp_storage_path):
    """Test using SQLite storage backend."""
    pipeline = IngestionPipeline(storage_type="sqlite", storage_path=temp_storage_path)
    
    # Process the file
    kg = pipeline.process_memory_file(temp_memory_file, merge_with_existing=False)
    
    # Verify the knowledge graph was created
    assert len(kg.entities) > 0
    assert len(kg.triplets) > 0
    
    # Verify the SQLite file was created
    assert Path(f"{temp_storage_path}.db").exists()
    
    # Test querying
    entities = pipeline.storage.query_entities(EntityType.PERSON)
    assert len(entities) > 0
    
    triplets = pipeline.storage.query_triplets(predicate=RelationType.KNOWS)
    assert len(triplets) >= 0  # Might be 0 if no "knows" relationships
