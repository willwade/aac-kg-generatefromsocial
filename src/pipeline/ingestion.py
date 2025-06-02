"""
Main ingestion pipeline for processing memory files into knowledge graphs.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from ..parsers.markdown_parser import MarkdownMemoryParser
from ..parsers.facebook_parser import FacebookDataParser
from ..parsers.ancestry_parser import AncestryGedcomParser
from ..extractors.triplet_extractor import TripletExtractor
from ..extractors.facebook_extractor import FacebookTripletExtractor
from ..extractors.ancestry_extractor import AncestryTripletExtractor
from ..storage.graph_store import GraphStore, JSONGraphStore, SQLiteGraphStore
from ..models.memory_schema import KnowledgeGraph, PersonMemory


class IngestionPipeline:
    """Main pipeline for ingesting memory files into knowledge graphs."""

    def __init__(
        self, storage_type: str = "json", storage_path: str = "data/knowledge_graph"
    ):
        self.markdown_parser = MarkdownMemoryParser()
        self.facebook_parser = FacebookDataParser()
        self.ancestry_parser = AncestryGedcomParser()
        self.extractor = TripletExtractor()
        self.facebook_extractor = FacebookTripletExtractor()
        self.ancestry_extractor = AncestryTripletExtractor()
        self.storage = self._create_storage(storage_type, storage_path)
        self.logger = self._setup_logging()

    def _create_storage(self, storage_type: str, storage_path: str) -> GraphStore:
        """Create appropriate storage backend."""
        if storage_type.lower() == "json":
            return JSONGraphStore(f"{storage_path}.json")
        elif storage_type.lower() == "sqlite":
            return SQLiteGraphStore(f"{storage_path}.db")
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the pipeline."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _parse_file_by_type(self, file_path: str) -> PersonMemory:
        """Parse file based on its type/extension."""
        from pathlib import Path

        file_path_obj = Path(file_path)

        if file_path_obj.suffix.lower() == ".md":
            return self.markdown_parser.parse_file(file_path)
        elif file_path_obj.suffix.lower() in [".ged", ".gedcom"]:
            return self.ancestry_parser.parse_gedcom_file(file_path)
        elif file_path_obj.is_dir():
            # Assume it's a Facebook export directory
            return self.facebook_parser.parse_export_directory(file_path)
        else:
            # Default to markdown parser
            return self.markdown_parser.parse_file(file_path)

    def _get_appropriate_extractor(self, memory: PersonMemory) -> TripletExtractor:
        """Get the appropriate extractor based on the memory source."""
        source = memory.metadata.get("source", "unknown")

        if source == "facebook":
            return self.facebook_extractor
        elif source == "ancestry_gedcom":
            return self.ancestry_extractor
        else:
            return self.extractor

    def process_memory_file(
        self, file_path: str, merge_with_existing: bool = True
    ) -> KnowledgeGraph:
        """
        Process a single memory file through the complete pipeline.

        Args:
            file_path: Path to the markdown memory file
            merge_with_existing: Whether to merge with existing knowledge graph

        Returns:
            The resulting knowledge graph
        """
        self.logger.info(f"Processing memory file: {file_path}")

        try:
            # Stage 1: Parse file based on type
            self.logger.info("Stage 1: Parsing file")
            memory = self._parse_file_by_type(file_path)
            self.logger.info(f"Parsed memory for: {memory.name}")

            # Stage 2: Extract triplets
            self.logger.info("Stage 2: Extracting triplets")
            extractor = self._get_appropriate_extractor(memory)
            new_kg = extractor.extract_from_memory(memory)
            self.logger.info(
                f"Extracted {len(new_kg.triplets)} triplets and {len(new_kg.entities)} entities"
            )

            # Stage 3: Merge with existing graph if requested
            if merge_with_existing:
                self.logger.info("Stage 3: Merging with existing knowledge graph")
                existing_kg = self.storage.load_graph()
                merged_kg = self._merge_knowledge_graphs(existing_kg, new_kg)
                self.logger.info(
                    f"Merged graph contains {len(merged_kg.triplets)} triplets and {len(merged_kg.entities)} entities"
                )
            else:
                merged_kg = new_kg

            # Stage 4: Store the result
            self.logger.info("Stage 4: Storing knowledge graph")
            self.storage.save_graph(merged_kg)
            self.logger.info("Pipeline completed successfully")

            return merged_kg

        except Exception as e:
            self.logger.error(f"Pipeline failed: {str(e)}")
            raise

    def _merge_knowledge_graphs(
        self, existing: KnowledgeGraph, new: KnowledgeGraph
    ) -> KnowledgeGraph:
        """
        Merge two knowledge graphs, handling entity deduplication.

        Args:
            existing: The existing knowledge graph
            new: The new knowledge graph to merge

        Returns:
            Merged knowledge graph
        """
        merged = KnowledgeGraph()

        # Copy existing entities and triplets
        for entity_id, entity in existing.entities.items():
            merged.add_entity(entity)

        for triplet in existing.triplets:
            merged.add_triplet(triplet)

        # Add new entities, checking for duplicates by name
        entity_name_mapping = {
            entity.name.lower(): entity.id for entity in existing.entities.values()
        }

        for entity_id, entity in new.entities.items():
            entity_name_lower = entity.name.lower()

            if entity_name_lower in entity_name_mapping:
                # Entity already exists, update the mapping for triplets
                existing_id = entity_name_mapping[entity_name_lower]
                self._update_triplet_references(new.triplets, entity_id, existing_id)
            else:
                # New entity, add it
                merged.add_entity(entity)
                entity_name_mapping[entity_name_lower] = entity_id

        # Add new triplets, avoiding exact duplicates
        existing_triplet_signatures = {
            (t.subject, t.predicate.value, t.object) for t in existing.triplets
        }

        for triplet in new.triplets:
            triplet_signature = (
                triplet.subject,
                triplet.predicate.value,
                triplet.object,
            )
            if triplet_signature not in existing_triplet_signatures:
                merged.add_triplet(triplet)

        # Merge metadata
        merged.metadata.update(existing.metadata)
        merged.metadata.update(new.metadata)
        merged.metadata["last_updated"] = new.metadata.get("created_at", "unknown")

        return merged

    def _update_triplet_references(
        self, triplets, old_entity_id: str, new_entity_id: str
    ) -> None:
        """Update entity references in triplets."""
        for triplet in triplets:
            if triplet.subject == old_entity_id:
                triplet.subject = new_entity_id
            if triplet.object == old_entity_id:
                triplet.object = new_entity_id

    def process_multiple_files(
        self, file_paths: list, merge_all: bool = True
    ) -> KnowledgeGraph:
        """
        Process multiple memory files.

        Args:
            file_paths: List of paths to memory files
            merge_all: Whether to merge all files into one graph

        Returns:
            The resulting knowledge graph
        """
        self.logger.info(f"Processing {len(file_paths)} memory files")

        if not file_paths:
            return KnowledgeGraph()

        # Process first file
        result_kg = self.process_memory_file(file_paths[0], merge_with_existing=False)

        # Process remaining files
        for file_path in file_paths[1:]:
            if merge_all:
                # Save current result and process next file with merging
                self.storage.save_graph(result_kg)
                result_kg = self.process_memory_file(
                    file_path, merge_with_existing=True
                )
            else:
                # Process each file separately
                self.process_memory_file(file_path, merge_with_existing=False)

        return result_kg

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the current knowledge graph."""
        kg = self.storage.load_graph()

        entity_counts = {}
        for entity in kg.entities.values():
            entity_type = entity.entity_type.value
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1

        predicate_counts = {}
        for triplet in kg.triplets:
            predicate = triplet.predicate.value
            predicate_counts[predicate] = predicate_counts.get(predicate, 0) + 1

        return {
            "total_entities": len(kg.entities),
            "total_triplets": len(kg.triplets),
            "entity_types": entity_counts,
            "predicate_types": predicate_counts,
            "metadata": kg.metadata,
        }

    def query_context_for_entity(
        self, entity_name: str, max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get contextual information for an entity (useful for AAC applications).

        Args:
            entity_name: Name of the entity to get context for
            max_depth: Maximum relationship depth to explore

        Returns:
            Dictionary containing contextual information
        """
        # Find the entity
        entities = self.storage.query_entities(name_pattern=entity_name)
        if not entities:
            return {"error": f'Entity "{entity_name}" not found'}

        target_entity = entities[0]  # Take the first match
        context = {
            "entity": {
                "name": target_entity.name,
                "type": target_entity.entity_type.value,
                "properties": target_entity.properties,
            },
            "relationships": {},
            "related_entities": [],
        }

        # Get direct relationships
        outgoing_triplets = self.storage.query_triplets(subject=target_entity.id)
        incoming_triplets = self.storage.query_triplets(object=target_entity.id)

        # Process outgoing relationships
        for triplet in outgoing_triplets:
            predicate = triplet.predicate.value
            if predicate not in context["relationships"]:
                context["relationships"][predicate] = []

            # Get the related entity or use literal value
            if triplet.object in self.storage.load_graph().entities:
                related_entity = self.storage.load_graph().entities[triplet.object]
                context["relationships"][predicate].append(
                    {
                        "name": related_entity.name,
                        "type": related_entity.entity_type.value,
                    }
                )
                context["related_entities"].append(related_entity.name)
            else:
                context["relationships"][predicate].append(
                    {"value": triplet.object, "type": "literal"}
                )

        # Process incoming relationships
        for triplet in incoming_triplets:
            predicate = f"is_{triplet.predicate.value}_of"
            if predicate not in context["relationships"]:
                context["relationships"][predicate] = []

            if triplet.subject in self.storage.load_graph().entities:
                related_entity = self.storage.load_graph().entities[triplet.subject]
                context["relationships"][predicate].append(
                    {
                        "name": related_entity.name,
                        "type": related_entity.entity_type.value,
                    }
                )
                if related_entity.name not in context["related_entities"]:
                    context["related_entities"].append(related_entity.name)

        return context
