"""
Ancestry/GEDCOM parser for genealogical data.
Converts GEDCOM files into PersonMemory objects focused on family relationships.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

from ..models.memory_schema import PersonMemory


class AncestryGedcomParser:
    """Parser for GEDCOM genealogical files from Ancestry.com and other sources."""

    def __init__(self):
        self.individuals = {}  # ID -> individual data
        self.families = {}  # ID -> family data
        self.current_record = None
        self.current_id = None

    def parse_gedcom_file(
        self, file_path: str, focus_person_name: Optional[str] = None
    ) -> PersonMemory:
        """
        Parse a GEDCOM file and extract family relationships.

        Args:
            file_path: Path to the GEDCOM file
            focus_person_name: Name of the person to focus on (if None, uses first person found)

        Returns:
            PersonMemory object with family relationships
        """
        gedcom_path = Path(file_path)

        # Parse the GEDCOM file
        self._parse_gedcom_content(gedcom_path)

        # Find the focus person
        focus_person = self._find_focus_person(focus_person_name)

        if not focus_person:
            # Create a generic memory if no focus person found
            memory = PersonMemory(name="Unknown Person")
            memory.metadata = {
                "source": "ancestry_gedcom",
                "file_path": str(gedcom_path),
                "total_individuals": len(self.individuals),
                "total_families": len(self.families),
            }
            return memory

        # Build PersonMemory for the focus person
        memory = self._build_person_memory(focus_person)
        memory.metadata = {
            "source": "ancestry_gedcom",
            "file_path": str(gedcom_path),
            "focus_person_id": focus_person["id"],
            "total_individuals": len(self.individuals),
            "total_families": len(self.families),
        }

        return memory

    def _parse_gedcom_content(self, file_path: Path) -> None:
        """Parse the GEDCOM file content."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse GEDCOM line format: LEVEL TAG [VALUE]
            parts = line.split(" ", 2)
            if len(parts) < 2:
                continue

            level = int(parts[0])
            tag = parts[1]
            value = parts[2] if len(parts) > 2 else ""

            self._process_gedcom_line(level, tag, value)

        # Store the last record
        self._finalize_current_record()

    def _finalize_current_record(self) -> None:
        """Store the current record if it exists."""
        if self.current_record and self.current_id:
            record_type = self.current_record.get("type")
            if record_type == "individual":
                self.individuals[self.current_id] = self.current_record
            elif record_type == "family":
                self.families[self.current_id] = self.current_record

    def _process_gedcom_line(self, level: int, tag: str, value: str) -> None:
        """Process a single GEDCOM line."""
        if level == 0:
            # Store the previous record before starting a new one
            self._finalize_current_record()

            # Start of new record
            if tag.startswith("@") and tag.endswith("@"):
                self.current_id = tag[1:-1]  # Remove @ symbols
                self.current_record = {"id": self.current_id}

                # Check if this is an individual or family record
                if value == "INDI":
                    self.current_record["type"] = "individual"
                elif value == "FAM":
                    self.current_record["type"] = "family"
            else:
                # Reset current record for non-@ level 0 lines
                self.current_record = None
                self.current_id = None

        elif level == 1 and self.current_record:
            # First-level tags
            if tag == "NAME":
                self.current_record["name"] = self._clean_name(value)
            elif tag == "SEX":
                self.current_record["sex"] = value
            elif tag == "BIRT":
                self.current_record["birth"] = {}
            elif tag == "DEAT":
                self.current_record["death"] = {}
            elif tag == "FACT":
                # Initialize fact processing - we'll capture the type in level 2
                self.current_record["_processing_fact"] = True
            elif tag == "HUSB":
                self.current_record["husband"] = (
                    value[1:-1] if value.startswith("@") else value
                )
            elif tag == "WIFE":
                self.current_record["wife"] = (
                    value[1:-1] if value.startswith("@") else value
                )
            elif tag == "CHIL":
                if "children" not in self.current_record:
                    self.current_record["children"] = []
                self.current_record["children"].append(
                    value[1:-1] if value.startswith("@") else value
                )
            elif tag == "FAMS":
                # Family as spouse
                if "spouse_families" not in self.current_record:
                    self.current_record["spouse_families"] = []
                self.current_record["spouse_families"].append(
                    value[1:-1] if value.startswith("@") else value
                )
            elif tag == "FAMC":
                # Family as child
                self.current_record["child_family"] = (
                    value[1:-1] if value.startswith("@") else value
                )

        elif level == 2 and self.current_record:
            # Second-level tags (dates, places, fact types)
            if tag == "DATE":
                if (
                    "birth" in self.current_record
                    and "date" not in self.current_record["birth"]
                ):
                    self.current_record["birth"]["date"] = value
                elif (
                    "death" in self.current_record
                    and "date" not in self.current_record["death"]
                ):
                    self.current_record["death"]["date"] = value
            elif tag == "PLAC":
                if (
                    "birth" in self.current_record
                    and "place" not in self.current_record["birth"]
                ):
                    self.current_record["birth"]["place"] = value
                elif (
                    "death" in self.current_record
                    and "place" not in self.current_record["death"]
                ):
                    self.current_record["death"]["place"] = value
            elif tag == "TYPE" and self.current_record.get("_processing_fact"):
                # Capture fact type (like AKA)
                if value == "AKA":
                    self.current_record["_processing_aka"] = True
            elif tag == "NOTE" and self.current_record.get("_processing_aka"):
                # Capture AKA name
                if "aka_names" not in self.current_record:
                    self.current_record["aka_names"] = []
                self.current_record["aka_names"].append(value.strip())
                # Clean up processing flags
                self.current_record.pop("_processing_fact", None)
                self.current_record.pop("_processing_aka", None)

    def _clean_name(self, name: str) -> str:
        """Clean GEDCOM name format (remove slashes around surname)."""
        # GEDCOM format: Given /Surname/ Suffix
        name = re.sub(r"/([^/]+)/", r"\1", name)  # Remove slashes around surname
        return " ".join(name.split())  # Normalize whitespace

    def _get_preferred_name(self, person: Dict) -> str:
        """Get the preferred name for a person, using AKA if available."""
        # If person has AKA names, use the first one (most commonly used)
        if "aka_names" in person and person["aka_names"]:
            return person["aka_names"][0]

        # Otherwise use the formal name
        return person.get("name", "Unknown Person")

    def _find_focus_person(self, focus_name: Optional[str]) -> Optional[Dict]:
        """Find the person to focus on in the family tree."""
        if not self.individuals:
            return None

        if focus_name:
            # Search for person by name with flexible matching
            focus_name_lower = focus_name.lower()
            focus_parts = focus_name_lower.split()

            print(
                f"Searching for: '{focus_name}' among {len(self.individuals)} individuals"
            )

            # Convert to ordered list to maintain file order (first occurrence wins)
            individuals_list = list(self.individuals.items())

            # Strategy: Prioritize file order over match type - the first matching person
            # in the file is most likely to be the focus person (especially in personal trees)

            # Single pass through the file, taking the first match of any type
            for person_id, person in individuals_list:
                person_name = person.get("name", "").lower()

                # Check for exact match first
                if focus_name_lower == person_name:
                    print(f"Found exact match (first in file): {person.get('name')}")
                    return person

                # Check for partial match (all parts must be in name)
                elif all(part in person_name for part in focus_parts):
                    print(f"Found partial match (first in file): {person.get('name')}")
                    return person

            # If no exact or partial match found, do a second pass for any part match
            for person_id, person in individuals_list:
                person_name = person.get("name", "").lower()
                if any(part in person_name for part in focus_parts):
                    print(f"Found name match (first in file): {person.get('name')}")
                    return person

        # If no specific person requested or not found, return the first person
        return next(iter(self.individuals.values()))

    def _build_person_memory(self, focus_person: Dict) -> PersonMemory:
        """Build PersonMemory object for the focus person."""
        name = focus_person.get("name", "Unknown Person")

        memory = PersonMemory(name=name)

        # Add basic info
        if "birth" in focus_person:
            birth_info = focus_person["birth"]
            birth_place = birth_info.get("place")
            if birth_place:
                memory.location = birth_place  # Use birth place as location

        # Extract family relationships
        self._extract_family_relationships(focus_person, memory)

        # Extract life events
        self._extract_life_events(focus_person, memory)

        # Extract places as interests
        self._extract_places_as_interests(focus_person, memory)

        return memory

    def _extract_family_relationships(
        self, focus_person: Dict, memory: PersonMemory
    ) -> None:
        """Extract family relationships and add them as people."""
        focus_id = focus_person["id"]

        # Parents (from child family)
        if "child_family" in focus_person:
            family_id = focus_person["child_family"]
            family = self.families.get(family_id, {})

            # Father
            father_id = family.get("husband")
            if father_id and father_id in self.individuals:
                father = self.individuals[father_id]
                father_name = self._get_preferred_name(father)
                memory.people.append(
                    {
                        "name": father_name,
                        "description": "Father",
                        "relationship_type": "parent",
                        "source": "ancestry_gedcom",
                    }
                )

            # Mother
            mother_id = family.get("wife")
            if mother_id and mother_id in self.individuals:
                mother = self.individuals[mother_id]
                mother_name = self._get_preferred_name(mother)
                memory.people.append(
                    {
                        "name": mother_name,
                        "description": "Mother",
                        "relationship_type": "parent",
                        "source": "ancestry_gedcom",
                    }
                )

            # Siblings
            siblings = family.get("children", [])
            for sibling_id in siblings:
                if sibling_id != focus_id and sibling_id in self.individuals:
                    sibling = self.individuals[sibling_id]
                    sibling_name = self._get_preferred_name(sibling)
                    memory.people.append(
                        {
                            "name": sibling_name,
                            "description": "Sibling",
                            "relationship_type": "sibling",
                            "source": "ancestry_gedcom",
                        }
                    )

        # Spouses and children (from spouse families)
        if "spouse_families" in focus_person:
            for family_id in focus_person["spouse_families"]:
                family = self.families.get(family_id, {})

                # Spouse
                spouse_id = None
                if family.get("husband") == focus_id:
                    spouse_id = family.get("wife")
                elif family.get("wife") == focus_id:
                    spouse_id = family.get("husband")

                if spouse_id and spouse_id in self.individuals:
                    spouse = self.individuals[spouse_id]
                    spouse_name = self._get_preferred_name(spouse)
                    memory.people.append(
                        {
                            "name": spouse_name,
                            "description": "Spouse",
                            "relationship_type": "spouse",
                            "source": "ancestry_gedcom",
                        }
                    )

                # Children
                children = family.get("children", [])
                for child_id in children:
                    if child_id in self.individuals:
                        child = self.individuals[child_id]
                        child_name = self._get_preferred_name(child)
                        memory.people.append(
                            {
                                "name": child_name,
                                "description": "Child",
                                "relationship_type": "child",
                                "source": "ancestry_gedcom",
                            }
                        )

    def _extract_life_events(self, focus_person: Dict, memory: PersonMemory) -> None:
        """Extract life events (birth, death, etc.)."""
        # Birth event
        if "birth" in focus_person:
            birth = focus_person["birth"]
            birth_date = birth.get("date", "Unknown date")
            birth_place = birth.get("place", "Unknown place")

            memory.events.append(
                {
                    "name": f"Birth of {memory.name}",
                    "description": f"Born on {birth_date} in {birth_place}",
                    "source": "ancestry_gedcom",
                }
            )

        # Death event
        if "death" in focus_person:
            death = focus_person["death"]
            death_date = death.get("date", "Unknown date")
            death_place = death.get("place", "Unknown place")

            memory.events.append(
                {
                    "name": f"Death of {memory.name}",
                    "description": f"Died on {death_date} in {death_place}",
                    "source": "ancestry_gedcom",
                }
            )

    def _extract_places_as_interests(
        self, focus_person: Dict, memory: PersonMemory
    ) -> None:
        """Extract places mentioned in the family tree as interests."""
        places = set()

        # Add birth and death places
        if "birth" in focus_person:
            birth_place = focus_person["birth"].get("place")
            if birth_place:
                places.add(birth_place)

        if "death" in focus_person:
            death_place = focus_person["death"].get("place")
            if death_place:
                places.add(death_place)

        # Add places from family members
        for person_info in memory.people:
            person_id = None
            # Find the person ID (this is a simplified approach)
            for pid, person_data in self.individuals.items():
                if person_data.get("name") == person_info["name"]:
                    person_id = pid
                    break

            if person_id:
                person_data = self.individuals[person_id]
                if "birth" in person_data:
                    birth_place = person_data["birth"].get("place")
                    if birth_place:
                        places.add(birth_place)

        # Add unique places as interests
        memory.interests.extend(
            [f"Family connection to {place}" for place in list(places)[:5]]
        )

    def get_family_statistics(self) -> Dict[str, Any]:
        """Get statistics about the parsed family tree."""
        return {
            "total_individuals": len(self.individuals),
            "total_families": len(self.families),
            "individuals_with_birth_dates": sum(
                1 for p in self.individuals.values() if "birth" in p
            ),
            "individuals_with_death_dates": sum(
                1 for p in self.individuals.values() if "death" in p
            ),
            "families_with_children": sum(
                1 for f in self.families.values() if "children" in f
            ),
        }
