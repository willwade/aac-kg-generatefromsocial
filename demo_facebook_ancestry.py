#!/usr/bin/env python3
"""
Demonstration of Facebook and Ancestry data integration.
Shows how the system can process social media and genealogical data.
"""

from src.pipeline.ingestion import IngestionPipeline
from src.models.memory_schema import EntityType, RelationType


def demo_facebook_integration():
    """Demonstrate Facebook data processing."""
    print("📱 Facebook Integration Demo")
    print("=" * 50)
    
    # Process the sample Facebook export
    pipeline = IngestionPipeline(storage_type="json", storage_path="data/facebook_demo")
    
    try:
        kg = pipeline.process_memory_file("examples/sample_facebook_export", merge_with_existing=False)
        
        print(f"✅ Processed Facebook export")
        print(f"   Entities: {len(kg.entities)}")
        print(f"   Triplets: {len(kg.triplets)}")
        
        # Show Facebook-specific relationships
        print("\n🔗 Facebook Relationships Found:")
        
        friends_triplets = [t for t in kg.triplets if t.predicate == RelationType.FRIENDS_WITH]
        if friends_triplets:
            print(f"   👥 Friends: {len(friends_triplets)}")
            for triplet in friends_triplets[:3]:  # Show first 3
                friend = kg.entities.get(triplet.object)
                if friend:
                    print(f"      • {friend.name}")
        
        work_triplets = [t for t in kg.triplets if t.predicate == RelationType.WORKS_AT]
        if work_triplets:
            print(f"   💼 Workplaces: {len(work_triplets)}")
            for triplet in work_triplets:
                workplace = kg.entities.get(triplet.object)
                if workplace:
                    print(f"      • {workplace.name}")
        
        interest_triplets = [t for t in kg.triplets if t.predicate == RelationType.HAS_INTEREST]
        if interest_triplets:
            print(f"   ❤️ Interests: {len(interest_triplets)}")
            for triplet in interest_triplets[:3]:  # Show first 3
                interest = kg.entities.get(triplet.object)
                if interest:
                    print(f"      • {interest.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Facebook demo failed: {e}")
        print("Make sure the sample Facebook export exists in examples/sample_facebook_export/")
        return False


def demo_ancestry_integration():
    """Demonstrate Ancestry/GEDCOM data processing."""
    print("\n\n🌳 Ancestry Integration Demo")
    print("=" * 50)
    
    # Process the sample GEDCOM file
    pipeline = IngestionPipeline(storage_type="json", storage_path="data/ancestry_demo")
    
    try:
        kg = pipeline.process_memory_file("examples/sample_family.ged", merge_with_existing=False)
        
        print(f"✅ Processed GEDCOM file")
        print(f"   Entities: {len(kg.entities)}")
        print(f"   Triplets: {len(kg.triplets)}")
        print(f"   👥 Total individuals in tree: {kg.metadata.get('total_individuals', 'Unknown')}")
        
        # Show family relationships
        print("\n👨‍👩‍👧‍👦 Family Relationships Found:")
        
        parent_triplets = [t for t in kg.triplets if t.predicate == RelationType.PARENT_OF]
        if parent_triplets:
            print(f"   👨‍👩‍👧‍👦 Parent relationships: {len(parent_triplets)}")
            for triplet in parent_triplets:
                parent = kg.entities.get(triplet.subject)
                child = kg.entities.get(triplet.object)
                if parent and child:
                    print(f"      • {parent.name} → {child.name}")
        
        spouse_triplets = [t for t in kg.triplets if t.predicate == RelationType.SPOUSE_OF]
        if spouse_triplets:
            print(f"   💑 Spouse relationships: {len(spouse_triplets)}")
            for triplet in spouse_triplets:
                spouse1 = kg.entities.get(triplet.subject)
                spouse2 = kg.entities.get(triplet.object)
                if spouse1 and spouse2:
                    print(f"      • {spouse1.name} ↔ {spouse2.name}")
        
        birth_triplets = [t for t in kg.triplets if t.predicate == RelationType.BORN_IN]
        if birth_triplets:
            print(f"   🏠 Birth locations: {len(birth_triplets)}")
            for triplet in birth_triplets[:3]:  # Show first 3
                person = kg.entities.get(triplet.subject)
                location = kg.entities.get(triplet.object)
                if person and location:
                    print(f"      • {person.name} born in {location.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ancestry demo failed: {e}")
        print("Make sure the sample GEDCOM file exists at examples/sample_family.ged")
        return False


def demo_combined_knowledge_graph():
    """Demonstrate combining multiple data sources."""
    print("\n\n🔗 Combined Knowledge Graph Demo")
    print("=" * 50)
    
    # Create a combined knowledge graph
    pipeline = IngestionPipeline(storage_type="json", storage_path="data/combined_demo")
    
    print("Processing multiple data sources...")
    
    sources_processed = 0
    
    # Process markdown memory file
    try:
        kg = pipeline.process_memory_file("examples/person-memory.md", merge_with_existing=False)
        print("✅ Processed markdown memory file")
        sources_processed += 1
    except Exception as e:
        print(f"⚠️ Could not process markdown file: {e}")
    
    # Process Facebook data if available
    try:
        kg = pipeline.process_memory_file("examples/sample_facebook_export", merge_with_existing=True)
        print("✅ Processed Facebook export")
        sources_processed += 1
    except Exception as e:
        print(f"⚠️ Could not process Facebook data: {e}")
    
    # Process Ancestry data if available
    try:
        kg = pipeline.process_memory_file("examples/sample_family.ged", merge_with_existing=True)
        print("✅ Processed GEDCOM file")
        sources_processed += 1
    except Exception as e:
        print(f"⚠️ Could not process GEDCOM file: {e}")
    
    if sources_processed > 0:
        # Show combined statistics
        stats = pipeline.get_statistics()
        print(f"\n📊 Combined Knowledge Graph Statistics:")
        print(f"   Total entities: {stats['total_entities']}")
        print(f"   Total triplets: {stats['total_triplets']}")
        print(f"   Data sources processed: {sources_processed}")
        
        print(f"\n📋 Entity types:")
        for entity_type, count in stats['entity_types'].items():
            print(f"   {entity_type}: {count}")
        
        print(f"\n🔗 Relationship types:")
        for predicate, count in sorted(stats['predicate_types'].items()):
            print(f"   {predicate}: {count}")
        
        return True
    else:
        print("❌ No data sources could be processed")
        return False


def demo_aac_applications():
    """Demonstrate AAC applications with multi-source data."""
    print("\n\n🎯 AAC Applications with Multi-Source Data")
    print("=" * 50)
    
    pipeline = IngestionPipeline(storage_type="json", storage_path="data/combined_demo")
    
    try:
        # Try to query for different types of entities
        print("🔍 Querying combined knowledge graph...")
        
        # Query for people
        people = pipeline.storage.query_entities(EntityType.PERSON)
        if people:
            print(f"\n👥 Found {len(people)} people in the knowledge graph:")
            for person in people[:5]:  # Show first 5
                print(f"   • {person.name}")
                
                # Get context for this person
                context = pipeline.query_context_for_entity(person.name)
                if 'relationships' in context:
                    rel_count = sum(len(rels) for rels in context['relationships'].values())
                    print(f"     ({rel_count} relationships)")
        
        # Show potential AAC suggestions
        print(f"\n💬 Example AAC Suggestions:")
        
        if people:
            sample_person = people[0]
            context = pipeline.query_context_for_entity(sample_person.name)
            
            if 'relationships' in context:
                relationships = context['relationships']
                
                if 'friendsWith' in relationships:
                    print(f"   📱 'Message {sample_person.name} on Facebook'")
                
                if 'spouseOf' in relationships:
                    print(f"   💑 'Call {sample_person.name}, your spouse'")
                
                if 'parentOf' in relationships or 'childOf' in relationships:
                    print(f"   👨‍👩‍👧‍👦 'Talk to {sample_person.name} about family'")
                
                if 'worksAt' in relationships:
                    print(f"   💼 'Discuss work with {sample_person.name}'")
        
        return True
        
    except Exception as e:
        print(f"❌ AAC demo failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Facebook and Ancestry Integration Demo")
    print("This demonstrates how the system can process multiple data sources")
    print("to build comprehensive knowledge graphs for AAC applications.\n")
    
    success_count = 0
    
    if demo_facebook_integration():
        success_count += 1
    
    if demo_ancestry_integration():
        success_count += 1
    
    if demo_combined_knowledge_graph():
        success_count += 1
    
    if demo_aac_applications():
        success_count += 1
    
    print(f"\n\n✅ Demo completed: {success_count}/4 sections successful")
    
    if success_count < 4:
        print("\n💡 To run all demos successfully:")
        print("1. Make sure example files exist in the examples/ directory")
        print("2. Run: python main.py process examples/person-memory.md")
        print("3. Then run this demo script again")
    else:
        print("\n🎉 All demos completed successfully!")
        print("\nThis shows how the system can now:")
        print("• Process Facebook data exports for social relationships")
        print("• Parse GEDCOM files for family genealogy")
        print("• Combine multiple data sources into unified knowledge graphs")
        print("• Generate context-aware AAC suggestions from diverse data")
