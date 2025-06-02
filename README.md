# AAC Knowledge Graph Generator

Generate personal knowledge graphs from social and life data to enable context-aware AAC (Augmentative and Alternative Communication) for users with communication disabilities.

## 🎯 Purpose

This system builds structured knowledge graphs from personal memory files, enabling:
- **Context-aware sentence suggestions** for AAC devices
- **Memory recall assistance** for users with cognitive disabilities
- **Personalized communication support** based on relationships and interests
- **Real-time contextual prompting** during conversations

## 🏗️ System Architecture

```
[Memory Files (.md)] → [Parser] → [Triplet Extractor] → [Knowledge Graph Store]
                                                              ↓
[AAC Interface] ← [Query Layer] ← [Context Engine] ← [Graph Database]
```

## 📋 Features

- **Multiple Data Sources**:
  - 📝 Markdown memory files (human-editable)
  - 📱 Facebook data exports (friends, posts, events, likes)
  - 🌳 Ancestry/GEDCOM files (family trees and genealogy)
- **Automatic Triplet Extraction**: Convert memories to structured relationships
- **Multiple Storage Backends**: JSON and SQLite support
- **Rich Query Interface**: Context-aware entity lookup
- **CLI Tools**: Complete command-line interface
- **Extensible Design**: Easy to add new data sources and formats

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/willwade/aac-kg-generatefromsocial.git
cd aac-kg-generatefromsocial

# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install -e .
```

### Basic Usage

1. **Create a memory file** (or use the example):
```bash
python main.py create-example
```

2. **Process different data sources**:
```bash
# Process markdown memory file
python main.py process examples/person-memory.md

# Process Facebook data export (directory)
python main.py process examples/sample_facebook_export --source-type facebook

# Process Ancestry GEDCOM file
python main.py process examples/sample_family.ged --source-type ancestry --focus-person "John Smith"
```

3. **Query the knowledge graph**:
```bash
python main.py query "Will Wade"
python main.py stats
python main.py list-entities
```

## 📊 Supported Data Sources

### 📝 Markdown Memory Files

Human-editable memory files use a structured Markdown format:

```markdown
# 📘 Personal Memory File – Your Name

## 🧑 Identity
- Name: Your Name
- Pronouns: they/them
- Lives in: Your City
- Works at: Your Company (Your Role)

## 👥 People
- Alice: friend, works at Google, loves hiking
- Bob: colleague, SLT, wears glasses, 2 children

## 🏢 Workplaces
- Current Company (2020–present)
- Previous Company (2018–2020)

## 💬 Events & Memories
- "Conference 2023" → met Alice, gave presentation
- "Team retreat" → with Bob, discussed new project

## ❤️ Interests
- programming, reading, hiking, photography

## 📚 Phrases I Often Say
- "That sounds like a plan."
- "Let's explore that idea."
```

### 📱 Facebook Data Exports

The system can process Facebook data exports to extract social relationships:

**How to get your Facebook data:**
1. Go to Facebook Settings & Privacy → Settings
2. Click "Your Facebook Information" → "Download Your Information"
3. Select data range and format (JSON recommended)
4. Include: Profile, Friends, Posts, Messages, Events, Likes and Reactions

**Supported Facebook data:**
- **Profile Information**: Name, location, work history, education
- **Friends List**: Social connections with timestamps
- **Posts**: Status updates, check-ins, shared content
- **Messages**: Frequent contacts from messenger
- **Events**: Attended events and activities
- **Likes**: Pages, interests, and preferences

**Processing Facebook data:**
```bash
# Extract your Facebook export to a directory
unzip facebook-export.zip -d facebook_data/

# Process the export
python main.py process facebook_data/ --source-type facebook
```

### 🌳 Ancestry/GEDCOM Files

Process genealogical data from Ancestry.com, FamilySearch, or any GEDCOM-compatible source:

**How to get your GEDCOM file:**
- **Ancestry.com**: Trees → Export Tree → GEDCOM
- **FamilySearch**: Family Tree → Export → GEDCOM
- **MyHeritage**: Family Tree → Manage Tree → Export to GEDCOM

**Supported genealogical data:**
- **Family Relationships**: Parents, children, spouses, siblings
- **Life Events**: Birth, death, marriage with dates and places
- **Locations**: Birth places, death places, family origins
- **Extended Family**: Automatically inferred relationships

**Processing GEDCOM data:**
```bash
# Process GEDCOM file focusing on a specific person
python main.py process family_tree.ged --source-type ancestry --focus-person "Your Name"

# Process without specifying focus person (uses first person found)
python main.py process family_tree.ged --source-type ancestry
```

## 🔧 CLI Commands

### Process Files
```bash
# Process a single memory file
python main.py process memory.md

# Process all .md files in a directory
python main.py process-directory memories/

# Process without merging with existing graph
python main.py process memory.md --no-merge
```

### Query and Explore
```bash
# Get context for a person
python main.py query "Alice"

# Get statistics about the graph
python main.py stats

# List all entities
python main.py list-entities

# List entities by type
python main.py list-entities --entity-type Person

# List relationships
python main.py list-triplets --predicate knows
```

### Storage Options
```bash
# Use SQLite storage (default: JSON)
python main.py --storage-type sqlite --storage-path data/graph.db process memory.md

# Custom storage location
python main.py --storage-path /path/to/graph process memory.md
```

## 🧠 Knowledge Graph Schema

### Entity Types
- **Person**: People in your life
- **Place**: Locations and venues
- **Event**: Memorable events and experiences
- **Organization**: Companies, institutions
- **Interest**: Hobbies and interests
- **Phrase**: Common expressions you use
- **Role**: Job titles and positions

### Relationship Types
- `knows` - Personal relationships
- `worksAt` - Employment relationships
- `livesIn` - Location relationships
- `hasInterest` - Interest relationships
- `attendedEvent` - Event participation
- `saidPhrase` - Speech patterns
- `hasRole` - Professional roles
- And many more...

## 📊 Example Output

After processing a memory file, you can query for context:

```bash
$ python main.py query "Daisy"

🔍 Context for: Daisy
==================================================
Type: Person
Properties:
  description: SLT, glasses, 2 children, co-authored Supercore

🔗 Relationships:
  is_knows_of:
    • Will Wade (Person)
  hasRole:
    • SLT (Role)
  wears:
    • glasses
  hasChildren:
    • 2
  coauthored:
    • Supercore (Memory)

👥 Related Entities: Will Wade, SLT, Supercore
```

## 🔌 Extending the System

### Adding New Data Sources

1. Create a new parser in `src/parsers/`
2. Implement the parsing logic to output `PersonMemory` objects
3. Register the parser in the pipeline

### Adding New Relationship Types

1. Add new relationships to `RelationType` enum in `src/models/memory_schema.py`
2. Update the triplet extractor to recognize new patterns
3. Update the CLI help text

### Custom Storage Backends

1. Inherit from `GraphStore` in `src/storage/graph_store.py`
2. Implement the required methods
3. Register in the pipeline

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

## 🎯 AAC Integration

This knowledge graph is designed to integrate with AAC applications:

### Context-Aware Suggestions
```python
from src.pipeline.ingestion import IngestionPipeline

pipeline = IngestionPipeline()
context = pipeline.query_context_for_entity("Daisy")

# Use context to generate relevant sentence suggestions:
# "Would you like to message Daisy, your SLT colleague?"
# "Daisy co-authored Supercore with you"
```

### Memory Prompting
```python
# When user mentions "conference"
events = pipeline.storage.query_entities(EntityType.EVENT, "conference")
# Suggest: "You met Daisy at the AAC conference in Liverpool"
```

## 🛣️ Roadmap

- [ ] **Social Media Connectors**: Import from LinkedIn, Facebook, Twitter
- [ ] **Calendar Integration**: Process calendar events automatically
- [ ] **Photo Analysis**: Extract context from image metadata
- [ ] **LLM Enhancement**: Use LLMs to improve triplet extraction
- [ ] **Real-time Updates**: Live sync with data sources
- [ ] **Privacy Controls**: Fine-grained data access controls
- [ ] **Mobile App**: Companion app for memory capture

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## 📞 Support

For questions or support:
- Email: wwade@acecentre.org.uk
- Issues: GitHub Issues
- Discussions: GitHub Discussions
