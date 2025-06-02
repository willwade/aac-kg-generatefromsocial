"""
Data models for the personal knowledge graph system.
Defines the structure for memory files, entities, and triplets.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class EntityType(str, Enum):
    """Types of entities in the knowledge graph."""

    PERSON = "Person"
    PLACE = "Place"
    EVENT = "Event"
    ORGANIZATION = "Organization"
    MEMORY = "Memory"
    PHRASE = "Phrase"
    INTEREST = "Interest"
    ROLE = "Role"
    POST = "Post"
    MESSAGE = "Message"
    PHOTO = "Photo"
    GROUP = "Group"
    PAGE = "Page"


class RelationType(str, Enum):
    """Types of relationships between entities."""

    KNOWS = "knows"
    WORKS_AT = "worksAt"
    HAS_ROLE = "hasRole"
    ATTENDED_EVENT = "attendedEvent"
    HAPPENED_IN = "happenedIn"
    HAS_COLLABORATOR = "hasCollaborator"
    HAS_INTEREST = "hasInterest"
    SAID_PHRASE = "saidPhrase"
    MET_AT = "metAt"
    IS_FAMILY_WITH = "isFamilyWith"
    LIVES_IN = "livesIn"
    HAS_CHILDREN = "hasChildren"
    WEARS = "wears"
    COAUTHORED = "coauthored"
    PARTNERED_WITH = "partneredWith"

    # Facebook-specific relationships
    FRIENDS_WITH = "friendsWith"
    POSTED = "posted"
    LIKED = "liked"
    COMMENTED_ON = "commentedOn"
    SHARED = "shared"
    TAGGED_IN = "taggedIn"
    MEMBER_OF = "memberOf"
    FOLLOWS = "follows"
    MESSAGED = "messaged"
    CHECKED_IN_AT = "checkedInAt"

    # Ancestry-specific relationships
    PARENT_OF = "parentOf"
    CHILD_OF = "childOf"
    SIBLING_OF = "siblingOf"
    SPOUSE_OF = "spouseOf"
    GRANDPARENT_OF = "grandparentOf"
    GRANDCHILD_OF = "grandchildOf"
    AUNT_UNCLE_OF = "auntUncleOf"
    NIECE_NEPHEW_OF = "nieceNephewOf"
    COUSIN_OF = "cousinOf"
    BORN_IN = "bornIn"
    DIED_IN = "diedIn"
    MARRIED_IN = "marriedIn"


class Entity(BaseModel):
    """Represents an entity in the knowledge graph."""

    id: str = Field(..., description="Unique identifier for the entity")
    name: str = Field(..., description="Human-readable name")
    entity_type: EntityType = Field(..., description="Type of entity")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Additional properties"
    )
    created_at: datetime = Field(default_factory=datetime.now)


class Triplet(BaseModel):
    """Represents a relationship triplet (subject, predicate, object)."""

    subject: str = Field(..., description="Subject entity ID")
    predicate: RelationType = Field(..., description="Relationship type")
    object: str = Field(..., description="Object entity ID or literal value")
    confidence: float = Field(default=1.0, description="Confidence score (0-1)")
    source: Optional[str] = Field(None, description="Source of this triplet")
    created_at: datetime = Field(default_factory=datetime.now)


class PersonMemory(BaseModel):
    """Structured representation of a person's memory file."""

    name: str = Field(..., description="Person's name")
    pronouns: Optional[str] = Field(None, description="Preferred pronouns")
    location: Optional[str] = Field(None, description="Current location")
    workplace: Optional[str] = Field(None, description="Current workplace")
    role: Optional[str] = Field(None, description="Current role/title")

    people: List[Dict[str, str]] = Field(
        default_factory=list, description="Known people and their details"
    )
    workplaces: List[Dict[str, str]] = Field(
        default_factory=list, description="Work history"
    )
    events: List[Dict[str, str]] = Field(
        default_factory=list, description="Memorable events"
    )
    interests: List[str] = Field(default_factory=list, description="Personal interests")
    phrases: List[str] = Field(default_factory=list, description="Common phrases")

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class KnowledgeGraph(BaseModel):
    """Complete knowledge graph representation."""

    entities: Dict[str, Entity] = Field(
        default_factory=dict, description="All entities by ID"
    )
    triplets: List[Triplet] = Field(
        default_factory=list, description="All relationship triplets"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Graph metadata")

    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the graph."""
        self.entities[entity.id] = entity

    def add_triplet(self, triplet: Triplet) -> None:
        """Add a triplet to the graph."""
        self.triplets.append(triplet)

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self.entities.get(entity_id)

    def get_triplets_by_subject(self, subject_id: str) -> List[Triplet]:
        """Get all triplets where the given entity is the subject."""
        return [t for t in self.triplets if t.subject == subject_id]

    def get_triplets_by_object(self, object_id: str) -> List[Triplet]:
        """Get all triplets where the given entity is the object."""
        return [t for t in self.triplets if t.object == object_id]


class MemorySection(BaseModel):
    """Represents a section from a memory markdown file."""

    title: str = Field(..., description="Section title")
    content: List[str] = Field(
        default_factory=list, description="Section content lines"
    )
    section_type: str = Field(
        ..., description="Type of section (identity, people, etc.)"
    )
