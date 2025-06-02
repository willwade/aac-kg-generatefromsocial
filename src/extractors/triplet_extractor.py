"""
Triplet extractor for converting PersonMemory objects into knowledge graph triplets.
"""

import re
from typing import List, Dict, Set
from datetime import datetime

from ..models.memory_schema import (
    PersonMemory, Entity, Triplet, EntityType, RelationType, KnowledgeGraph
)


class TripletExtractor:
    """Extracts triplets from PersonMemory objects."""
    
    def __init__(self):
        self.entity_counter = 0
        self.created_entities: Dict[str, str] = {}  # name -> entity_id mapping
    
    def extract_from_memory(self, memory: PersonMemory) -> KnowledgeGraph:
        """Extract a complete knowledge graph from a PersonMemory object."""
        kg = KnowledgeGraph()
        
        # Create the main person entity
        person_id = self._create_entity_id(memory.name)
        person_entity = Entity(
            id=person_id,
            name=memory.name,
            entity_type=EntityType.PERSON,
            properties={
                'pronouns': memory.pronouns,
                'location': memory.location,
                'workplace': memory.workplace,
                'role': memory.role
            }
        )
        kg.add_entity(person_entity)
        self.created_entities[memory.name] = person_id
        
        # Extract triplets from each section
        self._extract_identity_triplets(memory, kg, person_id)
        self._extract_people_triplets(memory, kg, person_id)
        self._extract_workplace_triplets(memory, kg, person_id)
        self._extract_event_triplets(memory, kg, person_id)
        self._extract_interest_triplets(memory, kg, person_id)
        self._extract_phrase_triplets(memory, kg, person_id)
        
        return kg
    
    def _create_entity_id(self, name: str) -> str:
        """Create a unique entity ID from a name."""
        # Normalize name to create ID
        entity_id = re.sub(r'[^a-zA-Z0-9]', '_', name.strip())
        entity_id = re.sub(r'_+', '_', entity_id)
        entity_id = entity_id.strip('_')
        
        # Ensure uniqueness
        if entity_id in self.created_entities.values():
            self.entity_counter += 1
            entity_id = f"{entity_id}_{self.entity_counter}"
        
        return entity_id
    
    def _get_or_create_entity(self, name: str, entity_type: EntityType, kg: KnowledgeGraph, 
                             properties: Dict = None) -> str:
        """Get existing entity ID or create new entity."""
        if name in self.created_entities:
            return self.created_entities[name]
        
        entity_id = self._create_entity_id(name)
        entity = Entity(
            id=entity_id,
            name=name,
            entity_type=entity_type,
            properties=properties or {}
        )
        kg.add_entity(entity)
        self.created_entities[name] = entity_id
        return entity_id
    
    def _extract_identity_triplets(self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str) -> None:
        """Extract triplets from identity information."""
        if memory.location:
            location_id = self._get_or_create_entity(memory.location, EntityType.PLACE, kg)
            kg.add_triplet(Triplet(
                subject=person_id,
                predicate=RelationType.LIVES_IN,
                object=location_id,
                source="identity"
            ))
        
        if memory.workplace:
            workplace_id = self._get_or_create_entity(memory.workplace, EntityType.ORGANIZATION, kg)
            kg.add_triplet(Triplet(
                subject=person_id,
                predicate=RelationType.WORKS_AT,
                object=workplace_id,
                source="identity"
            ))
        
        if memory.role:
            role_id = self._get_or_create_entity(memory.role, EntityType.ROLE, kg)
            kg.add_triplet(Triplet(
                subject=person_id,
                predicate=RelationType.HAS_ROLE,
                object=role_id,
                source="identity"
            ))
    
    def _extract_people_triplets(self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str) -> None:
        """Extract triplets from people relationships."""
        for person_info in memory.people:
            person_name = person_info['name']
            description = person_info.get('description', '')
            
            # Create person entity
            other_person_id = self._get_or_create_entity(person_name, EntityType.PERSON, kg)
            
            # Basic relationship
            kg.add_triplet(Triplet(
                subject=person_id,
                predicate=RelationType.KNOWS,
                object=other_person_id,
                source="people"
            ))
            
            # Parse description for additional relationships
            self._parse_person_description(description, other_person_id, kg)
    
    def _parse_person_description(self, description: str, person_id: str, kg: KnowledgeGraph) -> None:
        """Parse person description for additional triplets."""
        description_lower = description.lower()
        
        # Extract role information
        role_patterns = [
            r'(slt|speech therapist|teacher|manager|director|researcher|developer)',
            r'works? (?:as|at) ([^,]+)',
        ]
        
        for pattern in role_patterns:
            matches = re.findall(pattern, description_lower)
            for match in matches:
                role_name = match.strip()
                if role_name:
                    role_id = self._get_or_create_entity(role_name, EntityType.ROLE, kg)
                    kg.add_triplet(Triplet(
                        subject=person_id,
                        predicate=RelationType.HAS_ROLE,
                        object=role_id,
                        source="description"
                    ))
        
        # Extract physical attributes
        if 'glasses' in description_lower:
            kg.add_triplet(Triplet(
                subject=person_id,
                predicate=RelationType.WEARS,
                object="glasses",
                source="description"
            ))
        
        # Extract family information
        children_match = re.search(r'(\d+)\s*children?', description_lower)
        if children_match:
            kg.add_triplet(Triplet(
                subject=person_id,
                predicate=RelationType.HAS_CHILDREN,
                object=children_match.group(1),
                source="description"
            ))
        
        # Extract collaboration information
        if 'co-authored' in description_lower or 'coauthored' in description_lower:
            # Extract what was co-authored
            coauth_match = re.search(r'co-?authored\s+([^,]+)', description_lower)
            if coauth_match:
                work_name = coauth_match.group(1).strip()
                work_id = self._get_or_create_entity(work_name, EntityType.MEMORY, kg)
                kg.add_triplet(Triplet(
                    subject=person_id,
                    predicate=RelationType.COAUTHORED,
                    object=work_id,
                    source="description"
                ))
    
    def _extract_workplace_triplets(self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str) -> None:
        """Extract triplets from workplace history."""
        for workplace_info in memory.workplaces:
            company_name = workplace_info['company']
            years = workplace_info.get('years', '')
            
            company_id = self._get_or_create_entity(company_name, EntityType.ORGANIZATION, kg)
            kg.add_triplet(Triplet(
                subject=person_id,
                predicate=RelationType.WORKS_AT,
                object=company_id,
                source="workplaces",
                confidence=0.8  # Historical data might be less current
            ))
    
    def _extract_event_triplets(self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str) -> None:
        """Extract triplets from events and memories."""
        for event_info in memory.events:
            event_name = event_info['name']
            description = event_info.get('description', '')
            
            event_id = self._get_or_create_entity(event_name, EntityType.EVENT, kg)
            kg.add_triplet(Triplet(
                subject=person_id,
                predicate=RelationType.ATTENDED_EVENT,
                object=event_id,
                source="events"
            ))
            
            # Parse description for location and other details
            self._parse_event_description(description, event_id, person_id, kg)
    
    def _parse_event_description(self, description: str, event_id: str, person_id: str, kg: KnowledgeGraph) -> None:
        """Parse event description for additional triplets."""
        # Extract location information
        location_patterns = [
            r'in ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'at ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, description)
            for location in matches:
                location_id = self._get_or_create_entity(location, EntityType.PLACE, kg)
                kg.add_triplet(Triplet(
                    subject=event_id,
                    predicate=RelationType.HAPPENED_IN,
                    object=location_id,
                    source="event_description"
                ))
        
        # Extract people mentioned
        people_patterns = [
            r'met ([A-Z][a-z]+)',
            r'with ([A-Z][a-z]+)',
        ]
        
        for pattern in people_patterns:
            matches = re.findall(pattern, description)
            for person_name in matches:
                other_person_id = self._get_or_create_entity(person_name, EntityType.PERSON, kg)
                kg.add_triplet(Triplet(
                    subject=person_id,
                    predicate=RelationType.MET_AT,
                    object=other_person_id,
                    source="event_description"
                ))
    
    def _extract_interest_triplets(self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str) -> None:
        """Extract triplets from interests."""
        for interest in memory.interests:
            interest_id = self._get_or_create_entity(interest, EntityType.INTEREST, kg)
            kg.add_triplet(Triplet(
                subject=person_id,
                predicate=RelationType.HAS_INTEREST,
                object=interest_id,
                source="interests"
            ))
    
    def _extract_phrase_triplets(self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str) -> None:
        """Extract triplets from common phrases."""
        for phrase in memory.phrases:
            phrase_id = self._get_or_create_entity(phrase, EntityType.PHRASE, kg)
            kg.add_triplet(Triplet(
                subject=person_id,
                predicate=RelationType.SAID_PHRASE,
                object=phrase_id,
                source="phrases"
            ))
