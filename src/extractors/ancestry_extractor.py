"""
Ancestry-specific triplet extractor.
Extracts family relationships and genealogical data from Ancestry/GEDCOM data.
"""

import re
from typing import List, Dict, Set
from datetime import datetime

from ..models.memory_schema import (
    PersonMemory,
    Entity,
    Triplet,
    EntityType,
    RelationType,
    KnowledgeGraph,
)
from .triplet_extractor import TripletExtractor


class AncestryTripletExtractor(TripletExtractor):
    """Extracts triplets specifically from Ancestry/genealogical data."""

    def extract_from_memory(self, memory: PersonMemory) -> KnowledgeGraph:
        """Extract a complete knowledge graph from Ancestry PersonMemory."""
        kg = KnowledgeGraph()

        # Create the main person entity
        person_id = self._create_entity_id(memory.name)
        person_entity = Entity(
            id=person_id,
            name=memory.name,
            entity_type=EntityType.PERSON,
            properties={"location": memory.location, "source": "ancestry"},
        )
        kg.add_entity(person_entity)
        self.created_entities[memory.name] = person_id

        # Extract ancestry-specific triplets
        self._extract_family_relationships_triplets(memory, kg, person_id)
        self._extract_life_events_triplets(memory, kg, person_id)
        self._extract_genealogical_places_triplets(memory, kg, person_id)
        self._extract_family_interests_triplets(memory, kg, person_id)

        # Copy metadata from memory to knowledge graph
        kg.metadata.update(memory.metadata)

        return kg

    def _extract_family_relationships_triplets(
        self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str
    ) -> None:
        """Extract family relationships from genealogical data."""
        for person_info in memory.people:
            person_name = person_info["name"]
            description = person_info.get("description", "")
            relationship_type = person_info.get("relationship_type", "unknown")

            # Create family member entity
            family_member_id = self._get_or_create_entity(
                person_name, EntityType.PERSON, kg
            )

            # Map relationship types to specific genealogical relationships
            if relationship_type == "parent" or description.lower() in [
                "father",
                "mother",
            ]:
                if description.lower() == "father":
                    kg.add_triplet(
                        Triplet(
                            subject=family_member_id,
                            predicate=RelationType.PARENT_OF,
                            object=person_id,
                            source="ancestry_gedcom",
                        )
                    )
                    kg.add_triplet(
                        Triplet(
                            subject=person_id,
                            predicate=RelationType.CHILD_OF,
                            object=family_member_id,
                            source="ancestry_gedcom",
                        )
                    )
                elif description.lower() == "mother":
                    kg.add_triplet(
                        Triplet(
                            subject=family_member_id,
                            predicate=RelationType.PARENT_OF,
                            object=person_id,
                            source="ancestry_gedcom",
                        )
                    )
                    kg.add_triplet(
                        Triplet(
                            subject=person_id,
                            predicate=RelationType.CHILD_OF,
                            object=family_member_id,
                            source="ancestry_gedcom",
                        )
                    )
                else:
                    # Generic parent relationship
                    kg.add_triplet(
                        Triplet(
                            subject=family_member_id,
                            predicate=RelationType.PARENT_OF,
                            object=person_id,
                            source="ancestry_gedcom",
                        )
                    )

            elif relationship_type == "child" or description.lower() == "child":
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.PARENT_OF,
                        object=family_member_id,
                        source="ancestry_gedcom",
                    )
                )
                kg.add_triplet(
                    Triplet(
                        subject=family_member_id,
                        predicate=RelationType.CHILD_OF,
                        object=person_id,
                        source="ancestry_gedcom",
                    )
                )

            elif relationship_type == "sibling" or description.lower() == "sibling":
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.SIBLING_OF,
                        object=family_member_id,
                        source="ancestry_gedcom",
                    )
                )
                kg.add_triplet(
                    Triplet(
                        subject=family_member_id,
                        predicate=RelationType.SIBLING_OF,
                        object=person_id,
                        source="ancestry_gedcom",
                    )
                )

            elif relationship_type == "spouse" or description.lower() == "spouse":
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.SPOUSE_OF,
                        object=family_member_id,
                        source="ancestry_gedcom",
                    )
                )
                kg.add_triplet(
                    Triplet(
                        subject=family_member_id,
                        predicate=RelationType.SPOUSE_OF,
                        object=person_id,
                        source="ancestry_gedcom",
                    )
                )

            # Also add general family relationship
            kg.add_triplet(
                Triplet(
                    subject=person_id,
                    predicate=RelationType.IS_FAMILY_WITH,
                    object=family_member_id,
                    source="ancestry_gedcom",
                )
            )

    def _extract_life_events_triplets(
        self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str
    ) -> None:
        """Extract life events from genealogical data."""
        for event_info in memory.events:
            event_name = event_info["name"]
            description = event_info.get("description", "")

            # Create event entity
            event_id = self._get_or_create_entity(event_name, EntityType.EVENT, kg)

            # Determine event type and create appropriate relationships
            if "birth" in event_name.lower():
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.ATTENDED_EVENT,
                        object=event_id,
                        source="ancestry_gedcom",
                    )
                )

                # Extract birth location
                birth_location = self._extract_location_from_description(description)
                if birth_location:
                    location_id = self._get_or_create_entity(
                        birth_location, EntityType.PLACE, kg
                    )
                    kg.add_triplet(
                        Triplet(
                            subject=person_id,
                            predicate=RelationType.BORN_IN,
                            object=location_id,
                            source="ancestry_gedcom",
                        )
                    )
                    kg.add_triplet(
                        Triplet(
                            subject=event_id,
                            predicate=RelationType.HAPPENED_IN,
                            object=location_id,
                            source="ancestry_gedcom",
                        )
                    )

            elif "death" in event_name.lower():
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.ATTENDED_EVENT,
                        object=event_id,
                        source="ancestry_gedcom",
                    )
                )

                # Extract death location
                death_location = self._extract_location_from_description(description)
                if death_location:
                    location_id = self._get_or_create_entity(
                        death_location, EntityType.PLACE, kg
                    )
                    kg.add_triplet(
                        Triplet(
                            subject=person_id,
                            predicate=RelationType.DIED_IN,
                            object=location_id,
                            source="ancestry_gedcom",
                        )
                    )
                    kg.add_triplet(
                        Triplet(
                            subject=event_id,
                            predicate=RelationType.HAPPENED_IN,
                            object=location_id,
                            source="ancestry_gedcom",
                        )
                    )

            elif "marriage" in event_name.lower() or "wedding" in event_name.lower():
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.ATTENDED_EVENT,
                        object=event_id,
                        source="ancestry_gedcom",
                    )
                )

                # Extract marriage location
                marriage_location = self._extract_location_from_description(description)
                if marriage_location:
                    location_id = self._get_or_create_entity(
                        marriage_location, EntityType.PLACE, kg
                    )
                    kg.add_triplet(
                        Triplet(
                            subject=person_id,
                            predicate=RelationType.MARRIED_IN,
                            object=location_id,
                            source="ancestry_gedcom",
                        )
                    )

    def _extract_genealogical_places_triplets(
        self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str
    ) -> None:
        """Extract place relationships from genealogical data."""
        # Birth location (if available in memory.location)
        if memory.location:
            location_id = self._get_or_create_entity(
                memory.location, EntityType.PLACE, kg
            )
            kg.add_triplet(
                Triplet(
                    subject=person_id,
                    predicate=RelationType.BORN_IN,
                    object=location_id,
                    source="ancestry_gedcom",
                )
            )

        # Extract places from family member descriptions
        for person_info in memory.people:
            description = person_info.get("description", "")
            locations = self._extract_locations_from_family_description(description)

            for location in locations:
                location_id = self._get_or_create_entity(location, EntityType.PLACE, kg)
                # Create a general connection to family places
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.HAS_INTEREST,
                        object=location_id,
                        source="ancestry_family_places",
                        confidence=0.6,
                    )
                )

    def _extract_family_interests_triplets(
        self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str
    ) -> None:
        """Extract interests related to family heritage."""
        for interest in memory.interests:
            if "family connection" in interest.lower():
                # This is a place with family significance
                place_name = interest.replace("Family connection to", "").strip()
                place_id = self._get_or_create_entity(place_name, EntityType.PLACE, kg)

                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.HAS_INTEREST,
                        object=place_id,
                        source="ancestry_heritage",
                    )
                )
            else:
                # Regular interest
                interest_id = self._get_or_create_entity(
                    interest, EntityType.INTEREST, kg
                )
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.HAS_INTEREST,
                        object=interest_id,
                        source="ancestry_interests",
                    )
                )

    def _extract_location_from_description(self, description: str) -> str:
        """Extract location from event description."""
        # Look for patterns like "Born on DATE in PLACE" or "Died on DATE in PLACE"
        patterns = [
            r"in\s+([A-Z][a-zA-Z\s,]+?)(?:\s|$)",
            r"at\s+([A-Z][a-zA-Z\s,]+?)(?:\s|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                location = match.group(1).strip()
                # Clean up common trailing words
                location = re.sub(r"\s+(on|at|in)$", "", location)
                if len(location) > 2 and len(location) < 100:
                    return location

        return None

    def _extract_locations_from_family_description(self, description: str) -> List[str]:
        """Extract locations mentioned in family member descriptions."""
        # This could be enhanced to parse more complex genealogical descriptions
        locations = []

        # Look for place names in descriptions
        place_indicators = ["born in", "from", "lived in", "died in", "married in"]

        for indicator in place_indicators:
            pattern = f"{indicator}\\s+([A-Z][a-zA-Z\\s,]+?)(?:\\s|$|[.!?])"
            matches = re.findall(pattern, description, re.IGNORECASE)
            for match in matches:
                cleaned = match.strip()
                if len(cleaned) > 2 and len(cleaned) < 50:
                    locations.append(cleaned)

        return list(set(locations))

    def _infer_extended_family_relationships(
        self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str
    ) -> None:
        """Infer extended family relationships (grandparents, aunts, uncles, etc.)."""
        # This is a more advanced feature that could analyze the family tree structure
        # to infer relationships like grandparents, aunts, uncles, cousins, etc.
        # For now, we'll keep it simple and focus on direct relationships
        pass

    def _calculate_relationship_confidence(
        self, relationship_type: str, source: str
    ) -> float:
        """Calculate confidence score for genealogical relationships."""
        # GEDCOM data is generally quite reliable
        base_confidence = 0.95

        if relationship_type in ["parent", "child", "spouse"]:
            return base_confidence
        elif relationship_type in ["sibling"]:
            return base_confidence - 0.05
        elif relationship_type in ["grandparent", "grandchild"]:
            return base_confidence - 0.1
        else:
            return base_confidence - 0.2
