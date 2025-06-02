#!/usr/bin/env python3
"""
Demonstration of AAC integration capabilities.
Shows how the knowledge graph can be used for context-aware communication support.
"""

from src.pipeline.ingestion import IngestionPipeline
from src.models.memory_schema import EntityType, RelationType


def demo_context_aware_suggestions():
    """Demonstrate context-aware sentence suggestions."""
    print("🎯 AAC Integration Demo: Context-Aware Suggestions")
    print("=" * 60)
    
    # Initialize pipeline with the processed data
    pipeline = IngestionPipeline(storage_type="json", storage_path="data/knowledge_graph")
    
    # Scenario 1: User mentions "Daisy"
    print("\n📱 Scenario 1: User types 'Daisy'")
    print("-" * 40)
    
    context = pipeline.query_context_for_entity("Daisy")
    if 'error' not in context:
        print("🧠 Context retrieved:")
        print(f"   • {context['entity']['name']} is a {context['entity']['type']}")
        
        # Generate suggestions based on relationships
        relationships = context['relationships']
        suggestions = []
        
        if 'hasRole' in relationships:
            role = relationships['hasRole'][0]['name'] if relationships['hasRole'] else 'colleague'
            suggestions.append(f"Would you like to message Daisy, your {role}?")
        
        if 'coauthored' in relationships:
            work = relationships['coauthored'][0]['name'] if relationships['coauthored'] else 'project'
            suggestions.append(f"Daisy co-authored {work} with you.")
        
        if 'is_metAt_of' in relationships:
            suggestions.append("You met Daisy at a conference.")
        
        print("\n💬 Generated suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"   {i}. {suggestion}")
    
    # Scenario 2: User mentions "conference"
    print("\n\n📱 Scenario 2: User types 'conference'")
    print("-" * 40)
    
    events = pipeline.storage.query_entities(EntityType.EVENT, "conference")
    if events:
        event = events[0]
        print(f"🧠 Found event: {event.name}")
        
        # Get who was met at this event
        triplets = pipeline.storage.query_triplets(predicate=RelationType.MET_AT)
        met_people = []
        for triplet in triplets:
            if 'conference' in triplet.object.lower():
                person = pipeline.storage.load_graph().entities.get(triplet.subject)
                if person:
                    met_people.append(person.name)
        
        print("\n💬 Generated suggestions:")
        if met_people:
            print(f"   1. You met {', '.join(met_people)} at the conference.")
        print(f"   2. Tell me about the {event.name}.")
        print(f"   3. I want to talk about conferences.")


def demo_memory_prompting():
    """Demonstrate memory prompting for users with cognitive disabilities."""
    print("\n\n🧠 AAC Integration Demo: Memory Prompting")
    print("=" * 60)
    
    pipeline = IngestionPipeline(storage_type="json", storage_path="data/knowledge_graph")
    
    # Scenario: User seems confused about a person
    print("\n📱 Scenario: User asks 'Who is Keith?'")
    print("-" * 40)
    
    context = pipeline.query_context_for_entity("Keith Vertanen")
    if 'error' not in context:
        print("🧠 Memory prompt generated:")
        
        # Build a comprehensive memory prompt
        entity = context['entity']
        relationships = context['relationships']
        
        prompt_parts = [f"Keith Vertanen is a {entity['type'].lower()}"]
        
        if 'is_knows_of' in relationships:
            prompt_parts.append("you know")
        
        # Add context from relationships
        context_details = []
        if any('collaborator' in str(rel).lower() for rel in relationships.keys()):
            context_details.append("a collaborator")
        
        # Check for work mentions in phrases
        phrases_triplets = pipeline.storage.query_triplets(predicate=RelationType.SAID_PHRASE)
        keith_mentions = [t for t in phrases_triplets if 'keith' in t.object.lower()]
        if keith_mentions:
            context_details.append("someone you've worked with before")
        
        if context_details:
            prompt_parts.append("who is " + " and ".join(context_details))
        
        memory_prompt = " ".join(prompt_parts) + "."
        print(f"   💭 {memory_prompt}")
        
        # Add specific memory cues
        if keith_mentions:
            phrase_entity = pipeline.storage.load_graph().entities.get(keith_mentions[0].object)
            if phrase_entity:
                print(f"   💭 You often say: '{phrase_entity.name}'")


def demo_style_suggestions():
    """Demonstrate personalized communication style suggestions."""
    print("\n\n🗣️ AAC Integration Demo: Personal Style Suggestions")
    print("=" * 60)
    
    pipeline = IngestionPipeline(storage_type="json", storage_path="data/knowledge_graph")
    
    # Get user's common phrases
    phrases_triplets = pipeline.storage.query_triplets(predicate=RelationType.SAID_PHRASE)
    
    print("\n📱 Scenario: User wants to express agreement")
    print("-" * 40)
    
    if phrases_triplets:
        print("🧠 Your typical expressions:")
        kg = pipeline.storage.load_graph()
        for triplet in phrases_triplets:
            phrase_entity = kg.entities.get(triplet.object)
            if phrase_entity:
                print(f"   • '{phrase_entity.name}'")
        
        print("\n💬 Style-matched suggestions for agreement:")
        print("   1. That sounds like a plan.")  # Matches user's style
        print("   2. Could we explore that idea a bit more?")  # Matches user's style
        print("   3. I think that works well.")  # Generic alternative


def demo_relationship_context():
    """Demonstrate relationship-aware communication."""
    print("\n\n👥 AAC Integration Demo: Relationship-Aware Communication")
    print("=" * 60)
    
    pipeline = IngestionPipeline(storage_type="json", storage_path="data/knowledge_graph")
    
    # Get all people the user knows
    people = pipeline.storage.query_entities(EntityType.PERSON)
    main_user = next((p for p in people if p.name == "Will Wade"), None)
    
    if main_user:
        print("\n📱 Scenario: Suggesting communication based on relationships")
        print("-" * 40)
        
        # Get relationships
        knows_triplets = pipeline.storage.query_triplets(
            subject=main_user.id, 
            predicate=RelationType.KNOWS
        )
        
        kg = pipeline.storage.load_graph()
        for triplet in knows_triplets:
            person = kg.entities.get(triplet.object)
            if person:
                # Get context for this person
                person_context = pipeline.query_context_for_entity(person.name)
                
                # Generate relationship-appropriate suggestions
                suggestions = []
                
                if 'hasRole' in person_context.get('relationships', {}):
                    role_info = person_context['relationships']['hasRole']
                    if role_info:
                        role = role_info[0].get('name', 'colleague')
                        if role.lower() == 'slt':
                            suggestions.append(f"Ask {person.name} about speech therapy")
                        else:
                            suggestions.append(f"Discuss work with {person.name}")
                
                if 'is_family_with' in person_context.get('relationships', {}):
                    suggestions.append(f"Plan family time with {person.name}")
                elif person.name.lower() == 'lisa':  # From context, Lisa is wife
                    suggestions.append(f"Plan date night with {person.name}")
                
                if suggestions:
                    print(f"\n👤 {person.name}:")
                    for suggestion in suggestions:
                        print(f"   💬 {suggestion}")


if __name__ == "__main__":
    print("🚀 AAC Knowledge Graph Integration Demo")
    print("This demonstrates how the personal knowledge graph enables")
    print("context-aware communication support for AAC users.\n")
    
    try:
        demo_context_aware_suggestions()
        demo_memory_prompting()
        demo_style_suggestions()
        demo_relationship_context()
        
        print("\n\n✅ Demo completed successfully!")
        print("\nThis shows how the knowledge graph can power:")
        print("• Context-aware sentence suggestions")
        print("• Memory prompts for cognitive support")
        print("• Personalized communication style")
        print("• Relationship-appropriate messaging")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("Make sure you've processed the example memory file first:")
        print("python main.py process examples/person-memory.md")
