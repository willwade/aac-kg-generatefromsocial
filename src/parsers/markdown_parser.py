"""
Markdown parser for personal memory files.
Converts structured markdown into PersonMemory objects.
"""

import re
from typing import Dict, List, Optional
from pathlib import Path

from ..models.memory_schema import PersonMemory, MemorySection


class MarkdownMemoryParser:
    """Parser for personal memory markdown files."""
    
    def __init__(self):
        self.section_patterns = {
            'identity': r'##\s*🧑\s*Identity',
            'people': r'##\s*👥\s*People',
            'workplaces': r'##\s*🏢\s*Workplaces',
            'events': r'##\s*💬\s*Events\s*&\s*Memories',
            'interests': r'##\s*❤️\s*Interests',
            'phrases': r'##\s*📚\s*Phrases\s*I\s*Often\s*Say'
        }
    
    def parse_file(self, file_path: str) -> PersonMemory:
        """Parse a markdown memory file into a PersonMemory object."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> PersonMemory:
        """Parse markdown content into a PersonMemory object."""
        sections = self._extract_sections(content)
        
        # Initialize with defaults
        memory = PersonMemory(name="Unknown")
        
        # Parse each section
        for section in sections:
            if section.section_type == 'identity':
                self._parse_identity_section(section, memory)
            elif section.section_type == 'people':
                memory.people = self._parse_people_section(section)
            elif section.section_type == 'workplaces':
                memory.workplaces = self._parse_workplaces_section(section)
            elif section.section_type == 'events':
                memory.events = self._parse_events_section(section)
            elif section.section_type == 'interests':
                memory.interests = self._parse_interests_section(section)
            elif section.section_type == 'phrases':
                memory.phrases = self._parse_phrases_section(section)
        
        return memory
    
    def _extract_sections(self, content: str) -> List[MemorySection]:
        """Extract sections from markdown content."""
        sections = []
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            # Check if this line starts a new section
            section_type = self._identify_section(line)
            
            if section_type:
                # Save previous section if it exists
                if current_section:
                    sections.append(MemorySection(
                        title=current_section,
                        content=current_content,
                        section_type=current_section
                    ))
                
                # Start new section
                current_section = section_type
                current_content = []
            elif current_section and line.strip():
                # Add content to current section
                current_content.append(line.strip())
        
        # Add the last section
        if current_section:
            sections.append(MemorySection(
                title=current_section,
                content=current_content,
                section_type=current_section
            ))
        
        return sections
    
    def _identify_section(self, line: str) -> Optional[str]:
        """Identify which section type a line represents."""
        for section_type, pattern in self.section_patterns.items():
            if re.match(pattern, line, re.IGNORECASE):
                return section_type
        return None
    
    def _parse_identity_section(self, section: MemorySection, memory: PersonMemory) -> None:
        """Parse the identity section."""
        for line in section.content:
            if line.startswith('- Name:'):
                memory.name = line.replace('- Name:', '').strip()
            elif line.startswith('- Pronouns:'):
                memory.pronouns = line.replace('- Pronouns:', '').strip()
            elif line.startswith('- Lives in:'):
                memory.location = line.replace('- Lives in:', '').strip()
            elif line.startswith('- Works at:'):
                workplace_info = line.replace('- Works at:', '').strip()
                # Parse "Company (Role)" format
                if '(' in workplace_info and ')' in workplace_info:
                    parts = workplace_info.split('(')
                    memory.workplace = parts[0].strip()
                    memory.role = parts[1].replace(')', '').strip()
                else:
                    memory.workplace = workplace_info
    
    def _parse_people_section(self, section: MemorySection) -> List[Dict[str, str]]:
        """Parse the people section."""
        people = []
        for line in section.content:
            if line.startswith('- '):
                # Parse "Name: description" format
                person_info = line[2:].strip()
                if ':' in person_info:
                    name, description = person_info.split(':', 1)
                    people.append({
                        'name': name.strip(),
                        'description': description.strip()
                    })
        return people
    
    def _parse_workplaces_section(self, section: MemorySection) -> List[Dict[str, str]]:
        """Parse the workplaces section."""
        workplaces = []
        for line in section.content:
            if line.startswith('- '):
                # Parse "Company (years)" format
                workplace_info = line[2:].strip()
                if '(' in workplace_info and ')' in workplace_info:
                    parts = workplace_info.split('(')
                    company = parts[0].strip()
                    years = parts[1].replace(')', '').strip()
                    workplaces.append({
                        'company': company,
                        'years': years
                    })
                else:
                    workplaces.append({
                        'company': workplace_info,
                        'years': 'Unknown'
                    })
        return workplaces
    
    def _parse_events_section(self, section: MemorySection) -> List[Dict[str, str]]:
        """Parse the events section."""
        events = []
        for line in section.content:
            if line.startswith('- '):
                # Parse "Event" → description format
                event_info = line[2:].strip()
                if '→' in event_info:
                    parts = event_info.split('→', 1)
                    event_name = parts[0].strip().strip('"')
                    description = parts[1].strip()
                    events.append({
                        'name': event_name,
                        'description': description
                    })
                else:
                    events.append({
                        'name': event_info,
                        'description': ''
                    })
        return events
    
    def _parse_interests_section(self, section: MemorySection) -> List[str]:
        """Parse the interests section."""
        interests = []
        for line in section.content:
            if line.startswith('- '):
                # Split comma-separated interests
                interest_line = line[2:].strip()
                interests.extend([i.strip() for i in interest_line.split(',')])
        return interests
    
    def _parse_phrases_section(self, section: MemorySection) -> List[str]:
        """Parse the phrases section."""
        phrases = []
        for line in section.content:
            if line.startswith('- '):
                phrase = line[2:].strip().strip('"')
                phrases.append(phrase)
        return phrases
