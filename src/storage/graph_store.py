"""
Storage layer for the knowledge graph.
Supports SQLite, JSON, and in-memory storage with querying capabilities.
"""

import json
import sqlite3
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime

from ..models.memory_schema import KnowledgeGraph, Entity, Triplet, EntityType, RelationType


class GraphStore:
    """Base class for graph storage implementations."""
    
    def save_graph(self, kg: KnowledgeGraph) -> None:
        """Save a knowledge graph."""
        raise NotImplementedError
    
    def load_graph(self) -> KnowledgeGraph:
        """Load a knowledge graph."""
        raise NotImplementedError
    
    def query_entities(self, entity_type: Optional[EntityType] = None, 
                      name_pattern: Optional[str] = None) -> List[Entity]:
        """Query entities by type and/or name pattern."""
        raise NotImplementedError
    
    def query_triplets(self, subject: Optional[str] = None,
                      predicate: Optional[RelationType] = None,
                      object: Optional[str] = None) -> List[Triplet]:
        """Query triplets by subject, predicate, and/or object."""
        raise NotImplementedError


class JSONGraphStore(GraphStore):
    """JSON file-based storage for knowledge graphs."""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.kg: Optional[KnowledgeGraph] = None
    
    def save_graph(self, kg: KnowledgeGraph) -> None:
        """Save knowledge graph to JSON file."""
        self.kg = kg
        
        # Convert to serializable format
        data = {
            'entities': {
                entity_id: {
                    'id': entity.id,
                    'name': entity.name,
                    'entity_type': entity.entity_type.value,
                    'properties': entity.properties,
                    'created_at': entity.created_at.isoformat()
                }
                for entity_id, entity in kg.entities.items()
            },
            'triplets': [
                {
                    'subject': triplet.subject,
                    'predicate': triplet.predicate.value,
                    'object': triplet.object,
                    'confidence': triplet.confidence,
                    'source': triplet.source,
                    'created_at': triplet.created_at.isoformat()
                }
                for triplet in kg.triplets
            ],
            'metadata': kg.metadata
        }
        
        # Ensure directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_graph(self) -> KnowledgeGraph:
        """Load knowledge graph from JSON file."""
        if not self.file_path.exists():
            return KnowledgeGraph()
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reconstruct entities
        entities = {}
        for entity_id, entity_data in data.get('entities', {}).items():
            entity = Entity(
                id=entity_data['id'],
                name=entity_data['name'],
                entity_type=EntityType(entity_data['entity_type']),
                properties=entity_data.get('properties', {}),
                created_at=datetime.fromisoformat(entity_data['created_at'])
            )
            entities[entity_id] = entity
        
        # Reconstruct triplets
        triplets = []
        for triplet_data in data.get('triplets', []):
            triplet = Triplet(
                subject=triplet_data['subject'],
                predicate=RelationType(triplet_data['predicate']),
                object=triplet_data['object'],
                confidence=triplet_data.get('confidence', 1.0),
                source=triplet_data.get('source'),
                created_at=datetime.fromisoformat(triplet_data['created_at'])
            )
            triplets.append(triplet)
        
        kg = KnowledgeGraph(
            entities=entities,
            triplets=triplets,
            metadata=data.get('metadata', {})
        )
        
        self.kg = kg
        return kg
    
    def query_entities(self, entity_type: Optional[EntityType] = None,
                      name_pattern: Optional[str] = None) -> List[Entity]:
        """Query entities by type and/or name pattern."""
        if not self.kg:
            self.kg = self.load_graph()
        
        results = []
        for entity in self.kg.entities.values():
            # Filter by type
            if entity_type and entity.entity_type != entity_type:
                continue
            
            # Filter by name pattern
            if name_pattern and name_pattern.lower() not in entity.name.lower():
                continue
            
            results.append(entity)
        
        return results
    
    def query_triplets(self, subject: Optional[str] = None,
                      predicate: Optional[RelationType] = None,
                      object: Optional[str] = None) -> List[Triplet]:
        """Query triplets by subject, predicate, and/or object."""
        if not self.kg:
            self.kg = self.load_graph()
        
        results = []
        for triplet in self.kg.triplets:
            # Filter by subject
            if subject and triplet.subject != subject:
                continue
            
            # Filter by predicate
            if predicate and triplet.predicate != predicate:
                continue
            
            # Filter by object
            if object and triplet.object != object:
                continue
            
            results.append(triplet)
        
        return results


class SQLiteGraphStore(GraphStore):
    """SQLite-based storage for knowledge graphs."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize the SQLite database schema."""
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create entities table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    properties TEXT,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # Create triplets table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS triplets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    source TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (subject) REFERENCES entities (id)
                )
            ''')
            
            # Create indexes for better query performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_type ON entities (entity_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_name ON entities (name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_triplets_subject ON triplets (subject)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_triplets_predicate ON triplets (predicate)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_triplets_object ON triplets (object)')
            
            conn.commit()
    
    def save_graph(self, kg: KnowledgeGraph) -> None:
        """Save knowledge graph to SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Clear existing data
            cursor.execute('DELETE FROM triplets')
            cursor.execute('DELETE FROM entities')
            
            # Insert entities
            for entity in kg.entities.values():
                cursor.execute('''
                    INSERT INTO entities (id, name, entity_type, properties, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    entity.id,
                    entity.name,
                    entity.entity_type.value,
                    json.dumps(entity.properties),
                    entity.created_at.isoformat()
                ))
            
            # Insert triplets
            for triplet in kg.triplets:
                cursor.execute('''
                    INSERT INTO triplets (subject, predicate, object, confidence, source, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    triplet.subject,
                    triplet.predicate.value,
                    triplet.object,
                    triplet.confidence,
                    triplet.source,
                    triplet.created_at.isoformat()
                ))
            
            conn.commit()
    
    def load_graph(self) -> KnowledgeGraph:
        """Load knowledge graph from SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Load entities
            cursor.execute('SELECT id, name, entity_type, properties, created_at FROM entities')
            entities = {}
            for row in cursor.fetchall():
                entity_id, name, entity_type, properties_json, created_at = row
                entity = Entity(
                    id=entity_id,
                    name=name,
                    entity_type=EntityType(entity_type),
                    properties=json.loads(properties_json) if properties_json else {},
                    created_at=datetime.fromisoformat(created_at)
                )
                entities[entity_id] = entity
            
            # Load triplets
            cursor.execute('''
                SELECT subject, predicate, object, confidence, source, created_at 
                FROM triplets
            ''')
            triplets = []
            for row in cursor.fetchall():
                subject, predicate, obj, confidence, source, created_at = row
                triplet = Triplet(
                    subject=subject,
                    predicate=RelationType(predicate),
                    object=obj,
                    confidence=confidence,
                    source=source,
                    created_at=datetime.fromisoformat(created_at)
                )
                triplets.append(triplet)
            
            return KnowledgeGraph(entities=entities, triplets=triplets)
    
    def query_entities(self, entity_type: Optional[EntityType] = None,
                      name_pattern: Optional[str] = None) -> List[Entity]:
        """Query entities by type and/or name pattern."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = 'SELECT id, name, entity_type, properties, created_at FROM entities WHERE 1=1'
            params = []
            
            if entity_type:
                query += ' AND entity_type = ?'
                params.append(entity_type.value)
            
            if name_pattern:
                query += ' AND name LIKE ?'
                params.append(f'%{name_pattern}%')
            
            cursor.execute(query, params)
            
            entities = []
            for row in cursor.fetchall():
                entity_id, name, entity_type_str, properties_json, created_at = row
                entity = Entity(
                    id=entity_id,
                    name=name,
                    entity_type=EntityType(entity_type_str),
                    properties=json.loads(properties_json) if properties_json else {},
                    created_at=datetime.fromisoformat(created_at)
                )
                entities.append(entity)
            
            return entities
    
    def query_triplets(self, subject: Optional[str] = None,
                      predicate: Optional[RelationType] = None,
                      object: Optional[str] = None) -> List[Triplet]:
        """Query triplets by subject, predicate, and/or object."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT subject, predicate, object, confidence, source, created_at 
                FROM triplets WHERE 1=1
            '''
            params = []
            
            if subject:
                query += ' AND subject = ?'
                params.append(subject)
            
            if predicate:
                query += ' AND predicate = ?'
                params.append(predicate.value)
            
            if object:
                query += ' AND object = ?'
                params.append(object)
            
            cursor.execute(query, params)
            
            triplets = []
            for row in cursor.fetchall():
                subj, pred, obj, confidence, source, created_at = row
                triplet = Triplet(
                    subject=subj,
                    predicate=RelationType(pred),
                    object=obj,
                    confidence=confidence,
                    source=source,
                    created_at=datetime.fromisoformat(created_at)
                )
                triplets.append(triplet)
            
            return triplets
