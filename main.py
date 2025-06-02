#!/usr/bin/env python3
"""
Main CLI interface for the AAC Knowledge Graph Generator.
"""

import click
import json
from pathlib import Path
from typing import Optional

from src.pipeline.ingestion import IngestionPipeline
from src.models.memory_schema import EntityType, RelationType


@click.group()
@click.option(
    "--storage-type",
    default="json",
    type=click.Choice(["json", "sqlite"]),
    help="Storage backend type",
)
@click.option(
    "--storage-path", default="data/knowledge_graph", help="Path for storage files"
)
@click.pass_context
def cli(ctx, storage_type, storage_path):
    """AAC Knowledge Graph Generator - Build personal knowledge graphs from social data."""
    ctx.ensure_object(dict)
    ctx.obj["pipeline"] = IngestionPipeline(storage_type, storage_path)


@cli.command()
@click.argument("data_source", type=click.Path(exists=True))
@click.option("--no-merge", is_flag=True, help="Don't merge with existing graph")
@click.option(
    "--source-type",
    type=click.Choice(["auto", "markdown", "facebook", "ancestry"]),
    default="auto",
    help="Type of data source",
)
@click.option("--focus-person", help="For ancestry data: name of person to focus on")
def process(data_source, no_merge, source_type, focus_person):
    """Process a data source (markdown file, Facebook export, or GEDCOM file) into the knowledge graph."""
    pipeline = click.get_current_context().obj["pipeline"]

    click.echo(f"Processing data source: {data_source}")
    if source_type != "auto":
        click.echo(f"Source type: {source_type}")
    if focus_person:
        click.echo(f"Focus person: {focus_person}")

    try:
        # Handle special cases for ancestry data
        if source_type == "ancestry" or (
            source_type == "auto" and str(data_source).endswith((".ged", ".gedcom"))
        ):
            if focus_person:
                # For ancestry, we need to pass the focus person parameter
                memory = pipeline.ancestry_parser.parse_gedcom_file(
                    data_source, focus_person
                )
                extractor = pipeline._get_appropriate_extractor(memory)
                kg = extractor.extract_from_memory(memory)

                if not no_merge:
                    existing_kg = pipeline.storage.load_graph()
                    kg = pipeline._merge_knowledge_graphs(existing_kg, kg)

                pipeline.storage.save_graph(kg)
            else:
                kg = pipeline.process_memory_file(
                    data_source, merge_with_existing=not no_merge
                )
        else:
            kg = pipeline.process_memory_file(
                data_source, merge_with_existing=not no_merge
            )

        click.echo(f"✅ Successfully processed {data_source}")
        click.echo(f"   Entities: {len(kg.entities)}")
        click.echo(f"   Triplets: {len(kg.triplets)}")

        # Show source-specific information
        if kg.metadata.get("source") == "facebook":
            click.echo(f"   📱 Facebook data processed")
        elif kg.metadata.get("source") == "ancestry_gedcom":
            click.echo(f"   🌳 Ancestry/GEDCOM data processed")
            click.echo(
                f"   👥 Total individuals in tree: {kg.metadata.get('total_individuals', 'Unknown')}"
            )

    except Exception as e:
        click.echo(f"❌ Error processing data source: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@click.option("--pattern", default="*.md", help="File pattern to match")
def process_directory(directory, pattern):
    """Process all memory files in a directory."""
    pipeline = click.get_current_context().obj["pipeline"]

    directory_path = Path(directory)
    memory_files = list(directory_path.glob(pattern))

    if not memory_files:
        click.echo(f"No files matching '{pattern}' found in {directory}")
        return

    click.echo(f"Found {len(memory_files)} files to process")

    try:
        kg = pipeline.process_multiple_files([str(f) for f in memory_files])
        click.echo(f"✅ Successfully processed {len(memory_files)} files")
        click.echo(f"   Total entities: {len(kg.entities)}")
        click.echo(f"   Total triplets: {len(kg.triplets)}")
    except Exception as e:
        click.echo(f"❌ Error processing directory: {e}", err=True)
        raise click.Abort()


@cli.command()
def stats():
    """Show statistics about the current knowledge graph."""
    pipeline = click.get_current_context().obj["pipeline"]

    try:
        stats = pipeline.get_statistics()

        click.echo("📊 Knowledge Graph Statistics")
        click.echo("=" * 40)
        click.echo(f"Total Entities: {stats['total_entities']}")
        click.echo(f"Total Triplets: {stats['total_triplets']}")

        click.echo("\n📋 Entity Types:")
        for entity_type, count in stats["entity_types"].items():
            click.echo(f"  {entity_type}: {count}")

        click.echo("\n🔗 Relationship Types:")
        for predicate, count in stats["predicate_types"].items():
            click.echo(f"  {predicate}: {count}")

        if stats["metadata"]:
            click.echo("\n📝 Metadata:")
            for key, value in stats["metadata"].items():
                click.echo(f"  {key}: {value}")

    except Exception as e:
        click.echo(f"❌ Error getting statistics: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("entity_name")
@click.option("--depth", default=2, help="Maximum relationship depth to explore")
@click.option(
    "--format",
    "output_format",
    default="text",
    type=click.Choice(["text", "json"]),
    help="Output format",
)
def query(entity_name, depth, output_format):
    """Query contextual information for an entity."""
    pipeline = click.get_current_context().obj["pipeline"]

    try:
        context = pipeline.query_context_for_entity(entity_name, depth)

        if "error" in context:
            click.echo(f"❌ {context['error']}", err=True)
            return

        if output_format == "json":
            click.echo(json.dumps(context, indent=2))
        else:
            _display_context_text(context)

    except Exception as e:
        click.echo(f"❌ Error querying entity: {e}", err=True)
        raise click.Abort()


def _display_context_text(context):
    """Display context information in human-readable text format."""
    entity = context["entity"]
    click.echo(f"🔍 Context for: {entity['name']}")
    click.echo("=" * 50)
    click.echo(f"Type: {entity['type']}")

    if entity["properties"]:
        click.echo("Properties:")
        for key, value in entity["properties"].items():
            if value:
                click.echo(f"  {key}: {value}")

    click.echo("\n🔗 Relationships:")
    for relationship, targets in context["relationships"].items():
        click.echo(f"  {relationship}:")
        for target in targets:
            if "name" in target:
                click.echo(f"    • {target['name']} ({target['type']})")
            else:
                click.echo(f"    • {target['value']}")

    if context["related_entities"]:
        click.echo(f"\n👥 Related Entities: {', '.join(context['related_entities'])}")


@cli.command()
@click.option(
    "--entity-type",
    type=click.Choice([e.value for e in EntityType]),
    help="Filter by entity type",
)
@click.option("--name-pattern", help="Filter by name pattern")
def list_entities(entity_type, name_pattern):
    """List entities in the knowledge graph."""
    pipeline = click.get_current_context().obj["pipeline"]

    try:
        entity_type_enum = EntityType(entity_type) if entity_type else None
        entities = pipeline.storage.query_entities(entity_type_enum, name_pattern)

        if not entities:
            click.echo("No entities found matching the criteria.")
            return

        click.echo(f"📋 Found {len(entities)} entities:")
        click.echo("=" * 40)

        for entity in entities:
            click.echo(f"• {entity.name} ({entity.entity_type.value})")
            if entity.properties:
                for key, value in entity.properties.items():
                    if value:
                        click.echo(f"  {key}: {value}")

    except Exception as e:
        click.echo(f"❌ Error listing entities: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--subject", help="Filter by subject entity")
@click.option(
    "--predicate",
    type=click.Choice([r.value for r in RelationType]),
    help="Filter by relationship type",
)
@click.option("--object", help="Filter by object entity")
def list_triplets(subject, predicate, object):
    """List triplets in the knowledge graph."""
    pipeline = click.get_current_context().obj["pipeline"]

    try:
        predicate_enum = RelationType(predicate) if predicate else None
        triplets = pipeline.storage.query_triplets(subject, predicate_enum, object)

        if not triplets:
            click.echo("No triplets found matching the criteria.")
            return

        click.echo(f"🔗 Found {len(triplets)} triplets:")
        click.echo("=" * 50)

        for triplet in triplets:
            click.echo(
                f"• {triplet.subject} --{triplet.predicate.value}--> {triplet.object}"
            )
            if triplet.source:
                click.echo(f"  Source: {triplet.source}")
            if triplet.confidence < 1.0:
                click.echo(f"  Confidence: {triplet.confidence:.2f}")

    except Exception as e:
        click.echo(f"❌ Error listing triplets: {e}", err=True)
        raise click.Abort()


@cli.command()
def create_example():
    """Create an example memory file."""
    example_path = Path("examples/person-memory.md")

    if example_path.exists():
        click.echo(f"Example file already exists at: {example_path}")
        return

    # Ensure examples directory exists
    example_path.parent.mkdir(parents=True, exist_ok=True)

    click.echo(f"✅ Example memory file created at: {example_path}")
    click.echo(
        "You can now process it with: python main.py process examples/person-memory.md"
    )


if __name__ == "__main__":
    cli()
