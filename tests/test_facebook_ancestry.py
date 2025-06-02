"""
Tests for Facebook and Ancestry parsers and extractors.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path

from src.parsers.facebook_parser import FacebookDataParser
from src.parsers.ancestry_parser import AncestryGedcomParser
from src.extractors.facebook_extractor import FacebookTripletExtractor
from src.extractors.ancestry_extractor import AncestryTripletExtractor
from src.pipeline.ingestion import IngestionPipeline
from src.models.memory_schema import EntityType, RelationType


@pytest.fixture
def sample_facebook_export():
    """Create a sample Facebook export directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        export_dir = Path(temp_dir) / "facebook_export"
        export_dir.mkdir()
        
        # Create profile information
        profile_dir = export_dir / "profile_information"
        profile_dir.mkdir()
        profile_data = {
            "profile_v2": {
                "name": {"full_name": "Test User"},
                "places_lived": [{"place": {"name": "Test City"}}],
                "work": [{
                    "employer": {"name": "Test Company"},
                    "position": {"name": "Test Role"}
                }]
            }
        }
        with open(profile_dir / "profile_information.json", 'w') as f:
            json.dump(profile_data, f)
        
        # Create friends data
        friends_dir = export_dir / "friends"
        friends_dir.mkdir()
        friends_data = {
            "friends_v2": [
                {"name": "Friend One", "timestamp": 1640995200},
                {"name": "Friend Two", "timestamp": 1640995300}
            ]
        }
        with open(friends_dir / "friends.json", 'w') as f:
            json.dump(friends_data, f)
        
        yield str(export_dir)


@pytest.fixture
def sample_gedcom_content():
    """Sample GEDCOM content for testing."""
    return """0 HEAD
1 SOUR Test
0 @I1@ INDI
1 NAME Test /Person/
1 SEX M
1 BIRT
2 DATE 1 JAN 1980
2 PLAC Test City
1 FAMS @F1@
0 @I2@ INDI
1 NAME Test /Spouse/
1 SEX F
1 BIRT
2 DATE 1 JAN 1982
2 PLAC Another City
1 FAMS @F1@
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 MARR
2 DATE 1 JAN 2005
2 PLAC Wedding City
0 TRLR"""


@pytest.fixture
def temp_gedcom_file(sample_gedcom_content):
    """Create a temporary GEDCOM file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ged', delete=False) as f:
        f.write(sample_gedcom_content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


def test_facebook_parser(sample_facebook_export):
    """Test Facebook data parser."""
    parser = FacebookDataParser()
    memory = parser.parse_export_directory(sample_facebook_export)
    
    assert memory.name == "Test User"
    assert memory.location == "Test City"
    assert memory.workplace == "Test Company"
    assert memory.role == "Test Role"
    assert len(memory.people) == 2  # Two friends
    assert memory.metadata['source'] == 'facebook'


def test_facebook_extractor(sample_facebook_export):
    """Test Facebook triplet extractor."""
    parser = FacebookDataParser()
    memory = parser.parse_export_directory(sample_facebook_export)
    
    extractor = FacebookTripletExtractor()
    kg = extractor.extract_from_memory(memory)
    
    assert len(kg.entities) > 0
    assert len(kg.triplets) > 0
    
    # Check for Facebook-specific relationships
    friend_triplets = [t for t in kg.triplets if t.predicate == RelationType.FRIENDS_WITH]
    assert len(friend_triplets) == 2  # Two friends


def test_ancestry_parser(temp_gedcom_file):
    """Test Ancestry GEDCOM parser."""
    parser = AncestryGedcomParser()
    memory = parser.parse_gedcom_file(temp_gedcom_file)
    
    assert memory.name == "Test Person"
    assert len(memory.people) > 0  # Should have spouse
    assert memory.metadata['source'] == 'ancestry_gedcom'


def test_ancestry_extractor(temp_gedcom_file):
    """Test Ancestry triplet extractor."""
    parser = AncestryGedcomParser()
    memory = parser.parse_gedcom_file(temp_gedcom_file)
    
    extractor = AncestryTripletExtractor()
    kg = extractor.extract_from_memory(memory)
    
    assert len(kg.entities) > 0
    assert len(kg.triplets) > 0
    
    # Check for family relationships
    spouse_triplets = [t for t in kg.triplets if t.predicate == RelationType.SPOUSE_OF]
    assert len(spouse_triplets) > 0


def test_pipeline_facebook_integration(sample_facebook_export):
    """Test Facebook integration through the pipeline."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = os.path.join(temp_dir, "test_kg")
        pipeline = IngestionPipeline(storage_type="json", storage_path=storage_path)
        
        kg = pipeline.process_memory_file(sample_facebook_export, merge_with_existing=False)
        
        assert len(kg.entities) > 0
        assert len(kg.triplets) > 0
        assert kg.metadata.get('source') == 'facebook'


def test_pipeline_ancestry_integration(temp_gedcom_file):
    """Test Ancestry integration through the pipeline."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = os.path.join(temp_dir, "test_kg")
        pipeline = IngestionPipeline(storage_type="json", storage_path=storage_path)
        
        kg = pipeline.process_memory_file(temp_gedcom_file, merge_with_existing=False)
        
        assert len(kg.entities) > 0
        assert len(kg.triplets) > 0
        assert kg.metadata.get('source') == 'ancestry_gedcom'


def test_mixed_data_sources():
    """Test processing multiple data sources together."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = os.path.join(temp_dir, "test_kg")
        pipeline = IngestionPipeline(storage_type="json", storage_path=storage_path)
        
        # Create a simple markdown file
        md_file = Path(temp_dir) / "test.md"
        with open(md_file, 'w') as f:
            f.write("""# Personal Memory File – Mixed Test

## 🧑 Identity
- Name: Mixed Test User
- Lives in: Test Location

## 👥 People
- Test Friend: colleague, works at Test Corp

## ❤️ Interests
- testing, integration
""")
        
        # Process markdown file first
        kg1 = pipeline.process_memory_file(str(md_file), merge_with_existing=False)
        
        # Verify we can query the results
        stats = pipeline.get_statistics()
        assert stats['total_entities'] > 0
        assert stats['total_triplets'] > 0


def test_new_relationship_types():
    """Test that new relationship types are properly defined."""
    # Test Facebook relationships
    assert RelationType.FRIENDS_WITH == "friendsWith"
    assert RelationType.POSTED == "posted"
    assert RelationType.LIKED == "liked"
    assert RelationType.MESSAGED == "messaged"
    
    # Test Ancestry relationships
    assert RelationType.PARENT_OF == "parentOf"
    assert RelationType.CHILD_OF == "childOf"
    assert RelationType.SPOUSE_OF == "spouseOf"
    assert RelationType.SIBLING_OF == "siblingOf"
    assert RelationType.BORN_IN == "bornIn"


def test_new_entity_types():
    """Test that new entity types are properly defined."""
    assert EntityType.POST == "Post"
    assert EntityType.MESSAGE == "Message"
    assert EntityType.GROUP == "Group"
    assert EntityType.PAGE == "Page"
