"""
Facebook-specific triplet extractor.
Extracts social media relationships and activities from Facebook data.
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


class FacebookTripletExtractor(TripletExtractor):
    """Extracts triplets specifically from Facebook data."""

    def extract_from_memory(self, memory: PersonMemory) -> KnowledgeGraph:
        """Extract a complete knowledge graph from Facebook PersonMemory."""
        kg = KnowledgeGraph()

        # Create the main person entity
        person_id = self._create_entity_id(memory.name)
        person_entity = Entity(
            id=person_id,
            name=memory.name,
            entity_type=EntityType.PERSON,
            properties={
                "pronouns": memory.pronouns,
                "location": memory.location,
                "workplace": memory.workplace,
                "role": memory.role,
                "source": "facebook",
            },
        )
        kg.add_entity(person_entity)
        self.created_entities[memory.name] = person_id

        # Extract Facebook-specific triplets
        self._extract_identity_triplets(memory, kg, person_id)
        self._extract_facebook_friends_triplets(memory, kg, person_id)
        self._extract_facebook_workplace_triplets(memory, kg, person_id)
        self._extract_facebook_events_triplets(memory, kg, person_id)
        self._extract_facebook_interests_triplets(memory, kg, person_id)
        self._extract_facebook_posts_triplets(memory, kg, person_id)

        # Copy metadata from memory to knowledge graph
        kg.metadata.update(memory.metadata)

        return kg

    def _extract_facebook_friends_triplets(
        self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str
    ) -> None:
        """Extract Facebook friends relationships."""
        for person_info in memory.people:
            person_name = person_info["name"]
            description = person_info.get("description", "")
            relationship_type = person_info.get("relationship_type", "unknown")
            source = person_info.get("source", "facebook")

            # Create person entity
            other_person_id = self._get_or_create_entity(
                person_name, EntityType.PERSON, kg
            )

            # Determine relationship type based on Facebook data
            if relationship_type == "facebook_friend":
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.FRIENDS_WITH,
                        object=other_person_id,
                        source=source,
                    )
                )
            elif relationship_type == "frequent_contact":
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.MESSAGED,
                        object=other_person_id,
                        source=source,
                        confidence=0.9,
                    )
                )
                # Also add knows relationship
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.KNOWS,
                        object=other_person_id,
                        source=source,
                        confidence=0.9,
                    )
                )
            else:
                # Default to knows relationship
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.KNOWS,
                        object=other_person_id,
                        source=source,
                    )
                )

            # Parse description for additional context
            self._parse_facebook_person_description(description, other_person_id, kg)

    def _extract_facebook_workplace_triplets(
        self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str
    ) -> None:
        """Extract workplace relationships from Facebook data."""
        for workplace_info in memory.workplaces:
            company_name = workplace_info["company"]
            years = workplace_info.get("years", "")
            position = workplace_info.get("position", "")

            company_id = self._get_or_create_entity(
                company_name, EntityType.ORGANIZATION, kg
            )

            # Work relationship
            confidence = 0.9 if years != "Education" else 0.7
            kg.add_triplet(
                Triplet(
                    subject=person_id,
                    predicate=RelationType.WORKS_AT,
                    object=company_id,
                    source="facebook_profile",
                    confidence=confidence,
                )
            )

            # Position/role relationship
            if position and position != "Unknown":
                role_id = self._get_or_create_entity(position, EntityType.ROLE, kg)
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.HAS_ROLE,
                        object=role_id,
                        source="facebook_profile",
                    )
                )

    def _extract_facebook_events_triplets(
        self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str
    ) -> None:
        """Extract Facebook events and activities."""
        for event_info in memory.events:
            event_name = event_info["name"]
            description = event_info.get("description", "")
            source = event_info.get("source", "facebook")

            event_id = self._get_or_create_entity(event_name, EntityType.EVENT, kg)

            if source == "facebook_events":
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.ATTENDED_EVENT,
                        object=event_id,
                        source=source,
                    )
                )
            elif source == "facebook_posts":
                # Create post entity
                post_id = self._get_or_create_entity(event_name, EntityType.POST, kg)
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.POSTED,
                        object=post_id,
                        source=source,
                    )
                )

    def _extract_facebook_interests_triplets(
        self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str
    ) -> None:
        """Extract interests from Facebook data."""
        for interest in memory.interests:
            # Determine interest type
            if interest.startswith("Facebook group:"):
                # Group membership
                group_name = interest.replace("Facebook group:", "").strip()
                group_id = self._get_or_create_entity(group_name, EntityType.GROUP, kg)
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.MEMBER_OF,
                        object=group_id,
                        source="facebook_groups",
                    )
                )
            elif interest.startswith("#"):
                # Hashtag interest
                hashtag_id = self._get_or_create_entity(
                    interest, EntityType.INTEREST, kg
                )
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.HAS_INTEREST,
                        object=hashtag_id,
                        source="facebook_posts",
                    )
                )
            else:
                # Regular interest (liked page, place, etc.)
                interest_id = self._get_or_create_entity(
                    interest, EntityType.INTEREST, kg
                )
                kg.add_triplet(
                    Triplet(
                        subject=person_id,
                        predicate=RelationType.HAS_INTEREST,
                        object=interest_id,
                        source="facebook_likes",
                    )
                )

                # If it looks like a place, also create place entity
                if any(
                    keyword in interest.lower()
                    for keyword in ["restaurant", "cafe", "park", "museum", "theater"]
                ):
                    place_id = self._get_or_create_entity(
                        interest, EntityType.PLACE, kg
                    )
                    kg.add_triplet(
                        Triplet(
                            subject=person_id,
                            predicate=RelationType.CHECKED_IN_AT,
                            object=place_id,
                            source="facebook_places",
                            confidence=0.7,
                        )
                    )

    def _extract_facebook_posts_triplets(
        self, memory: PersonMemory, kg: KnowledgeGraph, person_id: str
    ) -> None:
        """Extract relationships from Facebook posts."""
        # Look for posts in events that might contain social information
        for event_info in memory.events:
            if event_info.get("source") == "facebook_posts":
                description = event_info.get("description", "")

                # Extract mentions of people
                mentioned_people = self._extract_people_mentions(description)
                for mentioned_person in mentioned_people:
                    person_entity_id = self._get_or_create_entity(
                        mentioned_person, EntityType.PERSON, kg
                    )
                    kg.add_triplet(
                        Triplet(
                            subject=person_id,
                            predicate=RelationType.KNOWS,
                            object=person_entity_id,
                            source="facebook_post_mentions",
                            confidence=0.6,
                        )
                    )

                # Extract locations
                locations = self._extract_location_mentions(description)
                for location in locations:
                    location_id = self._get_or_create_entity(
                        location, EntityType.PLACE, kg
                    )
                    kg.add_triplet(
                        Triplet(
                            subject=person_id,
                            predicate=RelationType.CHECKED_IN_AT,
                            object=location_id,
                            source="facebook_post_locations",
                            confidence=0.6,
                        )
                    )

    def _parse_facebook_person_description(
        self, description: str, person_id: str, kg: KnowledgeGraph
    ) -> None:
        """Parse Facebook person description for additional relationships."""
        if "friend since" in description.lower():
            # Extract friendship duration - could be used for relationship strength
            pass

        if "messages" in description.lower():
            # Extract message count for relationship strength
            message_match = re.search(r"(\d+)\s+messages", description)
            if message_match:
                message_count = int(message_match.group(1))
                # Higher message count = stronger relationship
                confidence = min(0.9, 0.5 + (message_count / 100))
                # This confidence could be used in the calling function

    def _extract_people_mentions(self, text: str) -> List[str]:
        """Extract potential people mentions from text."""
        # Look for patterns like "with John", "and Mary", etc.
        patterns = [
            r"with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"and\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"@([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        ]

        mentioned_people = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            mentioned_people.extend(matches)

        return list(set(mentioned_people))  # Remove duplicates

    def _extract_location_mentions(self, text: str) -> List[str]:
        """Extract potential location mentions from text."""
        # Look for patterns like "at Location", "in City", etc.
        patterns = [
            r"at\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|[.!?])",
            r"in\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|[.!?])",
            r"visited\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|[.!?])",
        ]

        locations = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            # Clean up matches (remove trailing words that don't look like places)
            for match in matches:
                cleaned = match.strip()
                if (
                    len(cleaned) > 2 and len(cleaned) < 50
                ):  # Reasonable place name length
                    locations.append(cleaned)

        return list(set(locations))  # Remove duplicates
