# Getting Started with AAC Knowledge Graph Generator

This guide will help you get up and running with the AAC Knowledge Graph Generator in just a few minutes.

## 🚀 Quick Start (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Process the Example Memory File
```bash
python main.py process examples/person-memory.md
```

### 3. Explore the Knowledge Graph
```bash
# See statistics
python main.py stats

# Query for a person
python main.py query "Will Wade"

# List all people
python main.py list-entities --entity-type Person
```

### 4. See AAC Integration Demo
```bash
python demo_aac_integration.py
```

## 📝 Creating Your Own Memory File

1. **Copy the example**:
```bash
cp examples/person-memory.md my-memory.md
```

2. **Edit with your information**:
```markdown
# 📘 Personal Memory File – Your Name

## 🧑 Identity
- Name: Your Name
- Pronouns: your/pronouns
- Lives in: Your City
- Works at: Your Company (Your Role)

## 👥 People
- Friend Name: description, relationship details
- Colleague Name: role, workplace, shared projects

## 🏢 Workplaces
- Current Company (2020–present)
- Previous Company (2018–2020)

## 💬 Events & Memories
- "Important Event" → what happened, who was there
- "Another Memory" → context and details

## ❤️ Interests
- hobby1, hobby2, hobby3

## 📚 Phrases I Often Say
- "Your common phrase"
- "Another expression you use"
```

3. **Process your file**:
```bash
python main.py process my-memory.md
```

## 🔧 Advanced Usage

### Multiple Storage Backends
```bash
# Use SQLite instead of JSON
python main.py --storage-type sqlite --storage-path data/my_graph process my-memory.md

# Custom storage location
python main.py --storage-path /path/to/my/graph process my-memory.md
```

### Batch Processing
```bash
# Process all .md files in a directory
python main.py process-directory memories/

# Process without merging (replace existing graph)
python main.py process my-memory.md --no-merge
```

### Querying and Analysis
```bash
# Get detailed context for any entity
python main.py query "Entity Name"

# Get JSON output for programmatic use
python main.py query "Entity Name" --format json

# List specific types of entities
python main.py list-entities --entity-type Person
python main.py list-entities --entity-type Event

# Search entities by name pattern
python main.py list-entities --name-pattern "conference"

# List specific relationships
python main.py list-triplets --predicate knows
python main.py list-triplets --subject "Will_Wade"
```

## 🎯 AAC Integration Examples

### Context-Aware Suggestions
```python
from src.pipeline.ingestion import IngestionPipeline

pipeline = IngestionPipeline()
context = pipeline.query_context_for_entity("Friend Name")

# Use context to generate suggestions:
# "Would you like to message [Friend], your [relationship]?"
```

### Memory Prompting
```python
# When user seems confused about a person
context = pipeline.query_context_for_entity("Person Name")
# Generate: "[Person] is someone you know who [relationship details]"
```

### Style Matching
```python
# Get user's common phrases for style-consistent suggestions
phrases = pipeline.storage.query_triplets(predicate=RelationType.SAID_PHRASE)
# Use these to match communication style in suggestions
```

## 📊 Understanding the Output

### Entity Types
- **Person**: People in your life
- **Place**: Locations (cities, venues)
- **Event**: Memorable events
- **Organization**: Companies, institutions
- **Interest**: Hobbies and interests
- **Phrase**: Your common expressions
- **Role**: Job titles and positions

### Relationship Types
- `knows` - Personal relationships
- `worksAt` - Employment
- `livesIn` - Location
- `hasInterest` - Interests
- `attendedEvent` - Event participation
- `saidPhrase` - Speech patterns
- `hasRole` - Professional roles
- And many more...

### Confidence Scores
- `1.0` - High confidence (direct from memory file)
- `0.8` - Medium confidence (historical data)
- Lower scores indicate less certain relationships

## 🧪 Testing Your Setup

Run the test suite to ensure everything is working:
```bash
pytest tests/ -v
```

## 🔍 Troubleshooting

### Common Issues

1. **Import errors**: Make sure you're in the project root directory
2. **File not found**: Check file paths are relative to project root
3. **Empty results**: Ensure you've processed a memory file first
4. **Permission errors**: Check write permissions for data directory

### Getting Help

1. Check the full README.md for detailed documentation
2. Run commands with `--help` for usage information
3. Look at the example files in `examples/`
4. Run the demo script to see expected behavior

## 🎉 Next Steps

1. **Create your personal memory file** with real data
2. **Experiment with queries** to understand your knowledge graph
3. **Try the AAC integration demo** to see practical applications
4. **Explore the code** in `src/` to understand how it works
5. **Consider extending** with new data sources or relationship types

Happy knowledge graphing! 🧠✨
