"""
Facebook data export parser.
Converts Facebook JSON exports into PersonMemory objects.
"""

import json
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from ..models.memory_schema import PersonMemory


class FacebookDataParser:
    """Parser for Facebook data exports."""
    
    def __init__(self):
        self.supported_files = {
            'profile_information/profile_information.json': self._parse_profile,
            'friends/friends.json': self._parse_friends,
            'posts/your_posts_1.json': self._parse_posts,
            'messages/inbox': self._parse_messages,
            'likes_and_reactions/pages.json': self._parse_liked_pages,
            'events/your_events.json': self._parse_events,
            'places/places_you_ve_created.json': self._parse_places,
            'groups/your_groups.json': self._parse_groups
        }
    
    def parse_export_directory(self, export_dir: str) -> PersonMemory:
        """
        Parse a Facebook data export directory.
        
        Args:
            export_dir: Path to the extracted Facebook export directory
            
        Returns:
            PersonMemory object with extracted data
        """
        export_path = Path(export_dir)
        
        # Initialize memory with defaults
        memory = PersonMemory(name="Facebook User")
        memory.metadata = {
            'source': 'facebook',
            'export_date': datetime.now().isoformat(),
            'export_path': str(export_path)
        }
        
        # Process each supported file type
        for relative_path, parser_func in self.supported_files.items():
            file_path = export_path / relative_path
            
            if file_path.exists():
                try:
                    parser_func(file_path, memory)
                except Exception as e:
                    print(f"Warning: Failed to parse {file_path}: {e}")
            elif file_path.suffix == '' and file_path.is_dir():
                # Handle directory-based data (like messages)
                try:
                    parser_func(file_path, memory)
                except Exception as e:
                    print(f"Warning: Failed to parse directory {file_path}: {e}")
        
        return memory
    
    def _parse_profile(self, file_path: Path, memory: PersonMemory) -> None:
        """Parse profile information."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        profile = data.get('profile_v2', {})
        
        # Extract basic info
        if 'name' in profile:
            memory.name = profile['name'].get('full_name', memory.name)
        
        # Extract location info
        if 'places_lived' in profile:
            places = profile['places_lived']
            if places:
                current_place = places[0]  # Most recent
                memory.location = current_place.get('place', {}).get('name', memory.location)
        
        # Extract work info
        if 'work' in profile:
            work_history = profile['work']
            if work_history:
                current_work = work_history[0]  # Most recent
                employer = current_work.get('employer', {}).get('name')
                position = current_work.get('position', {}).get('name')
                
                if employer:
                    memory.workplace = employer
                if position:
                    memory.role = position
                
                # Add all work history
                for work in work_history:
                    employer_name = work.get('employer', {}).get('name')
                    position_name = work.get('position', {}).get('name')
                    start_date = work.get('start_timestamp')
                    end_date = work.get('end_timestamp')
                    
                    if employer_name:
                        years = self._format_date_range(start_date, end_date)
                        memory.workplaces.append({
                            'company': employer_name,
                            'years': years,
                            'position': position_name or 'Unknown'
                        })
        
        # Extract education
        if 'education' in profile:
            for edu in profile['education']:
                school_name = edu.get('school', {}).get('name')
                if school_name:
                    memory.workplaces.append({
                        'company': school_name,
                        'years': 'Education',
                        'position': 'Student'
                    })
    
    def _parse_friends(self, file_path: Path, memory: PersonMemory) -> None:
        """Parse friends list."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        friends = data.get('friends_v2', [])
        
        for friend in friends:
            name = friend.get('name')
            timestamp = friend.get('timestamp')
            
            if name:
                friend_date = self._format_timestamp(timestamp) if timestamp else 'Unknown'
                memory.people.append({
                    'name': name,
                    'description': f'Facebook friend since {friend_date}',
                    'relationship_type': 'facebook_friend',
                    'source': 'facebook_friends'
                })
    
    def _parse_posts(self, file_path: Path, memory: PersonMemory) -> None:
        """Parse user's posts to extract interests and events."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        posts = data.get('status_updates_v2', []) + data.get('posts_v2', [])
        
        # Extract interests from post content
        interests_keywords = set()
        events_from_posts = []
        
        for post in posts[:50]:  # Limit to recent posts
            post_data = post.get('data', [{}])[0]
            post_text = post_data.get('post')
            timestamp = post.get('timestamp')
            
            if post_text:
                # Extract potential interests (hashtags, common topics)
                hashtags = re.findall(r'#(\w+)', post_text)
                interests_keywords.update(hashtags)
                
                # Look for event-like posts
                if any(keyword in post_text.lower() for keyword in 
                       ['went to', 'visited', 'at ', 'conference', 'meeting', 'party']):
                    event_date = self._format_timestamp(timestamp) if timestamp else 'Unknown date'
                    events_from_posts.append({
                        'name': f"Facebook post from {event_date}",
                        'description': post_text[:100] + '...' if len(post_text) > 100 else post_text,
                        'source': 'facebook_posts'
                    })
        
        # Add extracted interests
        memory.interests.extend(list(interests_keywords)[:10])  # Limit to top 10
        
        # Add events from posts
        memory.events.extend(events_from_posts[:5])  # Limit to 5 events
    
    def _parse_messages(self, messages_dir: Path, memory: PersonMemory) -> None:
        """Parse message threads to identify close contacts."""
        if not messages_dir.is_dir():
            return
        
        # Look for message threads
        for thread_dir in messages_dir.iterdir():
            if thread_dir.is_dir():
                message_file = thread_dir / 'message_1.json'
                if message_file.exists():
                    try:
                        with open(message_file, 'r', encoding='utf-8') as f:
                            thread_data = json.load(f)
                        
                        participants = thread_data.get('participants', [])
                        messages = thread_data.get('messages', [])
                        
                        # Identify frequent contacts (more than 10 messages)
                        if len(messages) > 10:
                            for participant in participants:
                                name = participant.get('name')
                                if name and name != memory.name:
                                    memory.people.append({
                                        'name': name,
                                        'description': f'Frequent Facebook messenger contact ({len(messages)} messages)',
                                        'relationship_type': 'frequent_contact',
                                        'source': 'facebook_messages'
                                    })
                    except Exception as e:
                        continue  # Skip problematic message files
    
    def _parse_liked_pages(self, file_path: Path, memory: PersonMemory) -> None:
        """Parse liked pages to extract interests."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        page_likes = data.get('page_likes_v2', [])
        
        # Extract page names as interests
        for like in page_likes[:20]:  # Limit to 20 most recent
            page_name = like.get('name')
            if page_name:
                memory.interests.append(page_name)
    
    def _parse_events(self, file_path: Path, memory: PersonMemory) -> None:
        """Parse events data."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        events = data.get('your_events_v2', [])
        
        for event in events:
            event_name = event.get('name')
            start_time = event.get('start_timestamp')
            
            if event_name:
                event_date = self._format_timestamp(start_time) if start_time else 'Unknown date'
                memory.events.append({
                    'name': event_name,
                    'description': f'Facebook event on {event_date}',
                    'source': 'facebook_events'
                })
    
    def _parse_places(self, file_path: Path, memory: PersonMemory) -> None:
        """Parse places/check-ins."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        places = data.get('places_created_v2', [])
        
        # Extract frequently visited places as interests
        place_names = []
        for place in places[:10]:  # Limit to 10
            place_name = place.get('name')
            if place_name:
                place_names.append(place_name)
        
        if place_names:
            memory.interests.extend(place_names)
    
    def _parse_groups(self, file_path: Path, memory: PersonMemory) -> None:
        """Parse group memberships."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        groups = data.get('groups_v2', [])
        
        # Extract group names as interests
        for group in groups[:10]:  # Limit to 10
            group_name = group.get('name')
            if group_name:
                memory.interests.append(f"Facebook group: {group_name}")
    
    def _format_timestamp(self, timestamp: Optional[int]) -> str:
        """Format Unix timestamp to readable date."""
        if not timestamp:
            return "Unknown date"
        
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, OSError):
            return "Unknown date"
    
    def _format_date_range(self, start_timestamp: Optional[int], end_timestamp: Optional[int]) -> str:
        """Format date range from timestamps."""
        start_date = self._format_timestamp(start_timestamp) if start_timestamp else "Unknown"
        end_date = self._format_timestamp(end_timestamp) if end_timestamp else "Present"
        
        if start_date == "Unknown" and end_date == "Present":
            return "Unknown period"
        elif end_date == "Present":
            return f"{start_date}–Present"
        else:
            return f"{start_date}–{end_date}"
