#!/usr/bin/env python
"""
Command Dictionary Tool for InkCraft RIP

This tool helps store, organize, and search discovered ESC/P commands during 
the reverse engineering process. It maintains a database of commands with their
parameters, descriptions, and usage examples.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

# Define command categories
CATEGORIES = {
    "INIT": "Initialization",
    "SETUP": "Printer Setup",
    "COLOR": "Color Management",
    "POSITION": "Positioning",
    "IMAGE": "Image Data",
    "WHITE": "White Ink Control",
    "QUALITY": "Print Quality",
    "MAINT": "Maintenance",
    "MISC": "Miscellaneous",
    "UNKNOWN": "Unknown Commands"
}

class CommandDictionary:
    """Command dictionary for storing and organizing discovered commands"""
    
    def __init__(self, db_file: Optional[str] = None):
        """Initialize the command dictionary"""
        self.db_file = db_file or "command_dictionary.json"
        self.commands = {}
        self.load_database()
        
    def load_database(self) -> bool:
        """Load the command database from file"""
        if not os.path.exists(self.db_file):
            self._create_empty_database()
            return True
            
        try:
            with open(self.db_file, 'r') as f:
                data = json.load(f)
                
            # Validate format
            if not isinstance(data, dict) or 'commands' not in data:
                print(f"Error: Invalid database format in {self.db_file}")
                self._create_empty_database()
                return False
                
            self.commands = data['commands']
            return True
                
        except Exception as e:
            print(f"Error loading database: {e}")
            self._create_empty_database()
            return False
    
    def _create_empty_database(self) -> None:
        """Create an empty command database"""
        self.commands = {}
        self.save_database()
    
    def save_database(self) -> bool:
        """Save the command database to file"""
        try:
            data = {
                "info": {
                    "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "commands_count": len(self.commands)
                },
                "commands": self.commands
            }
            
            with open(self.db_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            return True
                
        except Exception as e:
            print(f"Error saving database: {e}")
            return False
    
    def add_command(self, cmd_id: str, hex_sequence: str, 
                    description: str = "", category: str = "UNKNOWN",
                    parameters: List[Dict[str, Any]] = None,
                    examples: List[Dict[str, Any]] = None,
                    notes: str = "") -> bool:
        """
        Add a new command to the dictionary
        
        Args:
            cmd_id: Command identifier (e.g., "INIT_PRINTER")
            hex_sequence: Hex representation of the command (e.g., "1B 40")
            description: Description of what the command does
            category: Command category from CATEGORIES
            parameters: List of parameter definitions
            examples: List of usage examples
            notes: Additional notes about the command
            
        Returns:
            bool: True if added successfully, False otherwise
        """
        # Normalize hex sequence
        hex_sequence = hex_sequence.upper().replace('0X', '').replace(' ', '')
        if len(hex_sequence) % 2 != 0:
            print(f"Error: Invalid hex sequence '{hex_sequence}'")
            return False
        
        # Format for storage
        formatted_hex = ' '.join([hex_sequence[i:i+2] for i in range(0, len(hex_sequence), 2)])
        
        # Validate category
        if category not in CATEGORIES:
            print(f"Warning: Unknown category '{category}', using 'UNKNOWN'")
            category = "UNKNOWN"
        
        # Create command entry
        command = {
            "id": cmd_id,
            "hex": formatted_hex,
            "description": description,
            "category": category,
            "parameters": parameters or [],
            "examples": examples or [],
            "notes": notes,
            "date_added": datetime.now().strftime("%Y-%m-%d"),
            "verified": False
        }
        
        # Add to dictionary
        self.commands[cmd_id] = command
        self.save_database()
        
        print(f"Added command {cmd_id} ({formatted_hex})")
        return True
    
    def update_command(self, cmd_id: str, **kwargs) -> bool:
        """
        Update an existing command in the dictionary
        
        Args:
            cmd_id: Command identifier to update
            **kwargs: Fields to update
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        if cmd_id not in self.commands:
            print(f"Error: Command '{cmd_id}' not found")
            return False
        
        # Update specified fields
        for key, value in kwargs.items():
            if key == 'hex_sequence':
                # Normalize hex sequence
                hex_sequence = value.upper().replace('0X', '').replace(' ', '')
                if len(hex_sequence) % 2 != 0:
                    print(f"Error: Invalid hex sequence '{hex_sequence}'")
                    continue
                
                # Format for storage
                formatted_hex = ' '.join([hex_sequence[i:i+2] for i in range(0, len(hex_sequence), 2)])
                self.commands[cmd_id]['hex'] = formatted_hex
            else:
                self.commands[cmd_id][key] = value
        
        self.commands[cmd_id]['date_updated'] = datetime.now().strftime("%Y-%m-%d")
        self.save_database()
        
        print(f"Updated command {cmd_id}")
        return True
    
    def delete_command(self, cmd_id: str) -> bool:
        """
        Delete a command from the dictionary
        
        Args:
            cmd_id: Command identifier to delete
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        if cmd_id not in self.commands:
            print(f"Error: Command '{cmd_id}' not found")
            return False
        
        del self.commands[cmd_id]
        self.save_database()
        
        print(f"Deleted command {cmd_id}")
        return True
    
    def get_command(self, cmd_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a command by its identifier
        
        Args:
            cmd_id: Command identifier
            
        Returns:
            Command dictionary or None if not found
        """
        return self.commands.get(cmd_id)
    
    def search_commands(self, search_term: str, category: str = None) -> List[Dict[str, Any]]:
        """
        Search commands by text or hex pattern
        
        Args:
            search_term: Text to search for in ID, description, or hex
            category: Optional category to filter by
            
        Returns:
            List of matching commands
        """
        results = []
        
        for cmd_id, cmd in self.commands.items():
            # Skip if category filter is specified and doesn't match
            if category and cmd['category'] != category:
                continue
                
            # Search in ID, description, hex, and notes
            search_term_lower = search_term.lower()
            if (search_term_lower in cmd_id.lower() or
                search_term_lower in cmd['description'].lower() or
                search_term_lower in cmd['hex'].lower().replace(' ', '') or
                search_term_lower in cmd['notes'].lower()):
                results.append(cmd)
        
        return results
    
    def search_by_hex(self, hex_pattern: str) -> List[Dict[str, Any]]:
        """
        Search commands by exact hex pattern
        
        Args:
            hex_pattern: Hex pattern to search for
            
        Returns:
            List of matching commands
        """
        # Normalize input
        hex_pattern = hex_pattern.upper().replace('0X', '').replace(' ', '')
        
        results = []
        for cmd_id, cmd in self.commands.items():
            cmd_hex = cmd['hex'].replace(' ', '')
            if hex_pattern in cmd_hex:
                results.append(cmd)
        
        return results
    
    def list_commands(self, category: str = None) -> List[Dict[str, Any]]:
        """
        List all commands, optionally filtered by category
        
        Args:
            category: Optional category to filter by
            
        Returns:
            List of commands
        """
        if category:
            return [cmd for cmd in self.commands.values() if cmd['category'] == category]
        else:
            return list(self.commands.values())
    
    def import_from_parser(self, parser_file: str) -> int:
        """
        Import commands discovered by the ESC/P parser
        
        Args:
            parser_file: Parser output file
            
        Returns:
            Number of commands imported
        """
        try:
            with open(parser_file, 'r') as f:
                parser_data = json.load(f)
                
            if 'parsed_data' not in parser_data:
                print(f"Error: Invalid parser file format in {parser_file}")
                return 0
            
            count = 0
            for entry in parser_data['parsed_data']:
                if 'parsed_commands' not in entry:
                    continue
                    
                for cmd in entry['parsed_commands']:
                    if 'command' not in cmd or 'description' not in cmd:
                        continue
                        
                    # Generate a command ID from the description
                    desc = cmd['description']
                    cmd_id = desc.upper().replace(' ', '_')
                    if len(cmd_id) > 30:
                        cmd_id = cmd_id[:30]
                        
                    # Check if already exists
                    existing = self.search_by_hex(cmd['command'])
                    if existing:
                        continue
                        
                    # Add to dictionary
                    self.add_command(
                        cmd_id=cmd_id,
                        hex_sequence=cmd['command'],
                        description=desc,
                        category=self._categorize_command(desc),
                        parameters=[{
                            "name": "params",
                            "description": "Command parameters",
                            "value": cmd.get('parameters', '')
                        }]
                    )
                    count += 1
            
            return count
                
        except Exception as e:
            print(f"Error importing from parser file: {e}")
            return 0
    
    def _categorize_command(self, description: str) -> str:
        """
        Attempt to categorize a command based on its description
        
        Args:
            description: Command description
            
        Returns:
            Category identifier
        """
        description = description.lower()
        
        if any(x in description for x in ['initialize', 'reset']):
            return 'INIT'
        elif any(x in description for x in ['color', 'ink']):
            return 'COLOR'
        elif any(x in description for x in ['white']):
            return 'WHITE'
        elif any(x in description for x in ['position', 'horizontal', 'vertical']):
            return 'POSITION'
        elif any(x in description for x in ['image', 'graphics', 'bit image']):
            return 'IMAGE'
        elif any(x in description for x in ['quality', 'resolution']):
            return 'QUALITY'
        elif any(x in description for x in ['unit', 'page', 'format']):
            return 'SETUP'
        else:
            return 'UNKNOWN'
    
    def print_command(self, cmd_id: str) -> None:
        """Print a command in a readable format"""
        cmd = self.get_command(cmd_id)
        if not cmd:
            print(f"Command '{cmd_id}' not found")
            return
            
        print("\n" + "=" * 50)
        print(f"Command: {cmd['id']}")
        print("=" * 50)
        print(f"Hex: {cmd['hex']}")
        print(f"Category: {cmd['category']} ({CATEGORIES[cmd['category']]})")
        print(f"Description: {cmd['description']}")
        
        if cmd['parameters']:
            print("\nParameters:")
            for param in cmd['parameters']:
                print(f"  - {param['name']}: {param['description']}")
                if 'value' in param:
                    print(f"    Value: {param['value']}")
        
        if cmd['examples']:
            print("\nExamples:")
            for i, example in enumerate(cmd['examples']):
                print(f"  Example {i+1}: {example['description']}")
                print(f"    Command: {example['command']}")
                if 'result' in example:
                    print(f"    Result: {example['result']}")
        
        if cmd['notes']:
            print(f"\nNotes: {cmd['notes']}")
            
        print(f"\nAdded: {cmd['date_added']}")
        if 'date_updated' in cmd:
            print(f"Last Updated: {cmd['date_updated']}")
            
        print(f"Verified: {'Yes' if cmd['verified'] else 'No'}")
        print("-" * 50)

def main():
    parser = argparse.ArgumentParser(description="InkCraft RIP Command Dictionary Tool")
    
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new command')
    add_parser.add_argument('id', help='Command identifier (e.g., INIT_PRINTER)')
    add_parser.add_argument('hex', help='Hex sequence (e.g., "1B 40")')
    add_parser.add_argument('--desc', help='Command description')
    add_parser.add_argument('--cat', help='Command category', choices=CATEGORIES.keys())
    add_parser.add_argument('--notes', help='Additional notes')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update an existing command')
    update_parser.add_argument('id', help='Command identifier to update')
    update_parser.add_argument('--hex', help='Hex sequence')
    update_parser.add_argument('--desc', help='Command description')
    update_parser.add_argument('--cat', help='Command category', choices=CATEGORIES.keys())
    update_parser.add_argument('--notes', help='Additional notes')
    update_parser.add_argument('--verified', action='store_true', help='Mark as verified')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a command')
    delete_parser.add_argument('id', help='Command identifier to delete')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get a command')
    get_parser.add_argument('id', help='Command identifier')
    
    # Search commands
    search_parser = subparsers.add_parser('search', help='Search commands')
    search_parser.add_argument('term', help='Search term')
    search_parser.add_argument('--cat', help='Filter by category', choices=CATEGORIES.keys())
    
    # Search by hex
    hex_parser = subparsers.add_parser('hex', help='Search by hex pattern')
    hex_parser.add_argument('pattern', help='Hex pattern')
    
    # List commands
    list_parser = subparsers.add_parser('list', help='List commands')
    list_parser.add_argument('--cat', help='Filter by category', choices=CATEGORIES.keys())
    
    # Import from parser
    import_parser = subparsers.add_parser('import', help='Import from parser output')
    import_parser.add_argument('file', help='Parser output file')
    
    # Add example
    example_parser = subparsers.add_parser('add-example', help='Add an example for a command')
    example_parser.add_argument('id', help='Command identifier')
    example_parser.add_argument('--desc', required=True, help='Example description')
    example_parser.add_argument('--cmd', required=True, help='Example command')
    example_parser.add_argument('--result', help='Example result')
    
    # Database file
    parser.add_argument('--db', help='Database file path', default='command_dictionary.json')
    
    args = parser.parse_args()
    
    # Create dictionary
    dictionary = CommandDictionary(args.db)
    
    # Process commands
    if args.command == 'add':
        dictionary.add_command(
            args.id, args.hex, 
            description=args.desc or "", 
            category=args.cat or "UNKNOWN",
            notes=args.notes or ""
        )
    
    elif args.command == 'update':
        updates = {}
        if args.hex:
            updates['hex_sequence'] = args.hex
        if args.desc:
            updates['description'] = args.desc
        if args.cat:
            updates['category'] = args.cat
        if args.notes:
            updates['notes'] = args.notes
        if args.verified:
            updates['verified'] = True
            
        dictionary.update_command(args.id, **updates)
    
    elif args.command == 'delete':
        dictionary.delete_command(args.id)
    
    elif args.command == 'get':
        dictionary.print_command(args.id)
    
    elif args.command == 'search':
        results = dictionary.search_commands(args.term, args.cat)
        print(f"\nFound {len(results)} command(s) matching '{args.term}':")
        for cmd in results:
            print(f"  {cmd['id']}: {cmd['hex']} - {cmd['description']}")
    
    elif args.command == 'hex':
        results = dictionary.search_by_hex(args.pattern)
        print(f"\nFound {len(results)} command(s) with hex pattern '{args.pattern}':")
        for cmd in results:
            print(f"  {cmd['id']}: {cmd['hex']} - {cmd['description']}")
    
    elif args.command == 'list':
        results = dictionary.list_commands(args.cat)
        category_name = CATEGORIES[args.cat] if args.cat else "all categories"
        print(f"\nListing {len(results)} command(s) from {category_name}:")
        for cmd in results:
            print(f"  {cmd['id']}: {cmd['hex']} - {cmd['description']}")
    
    elif args.command == 'import':
        count = dictionary.import_from_parser(args.file)
        print(f"Imported {count} new commands from {args.file}")
    
    elif args.command == 'add-example':
        cmd = dictionary.get_command(args.id)
        if not cmd:
            print(f"Command '{args.id}' not found")
            return 1
            
        example = {
            "description": args.desc,
            "command": args.cmd
        }
        if args.result:
            example["result"] = args.result
            
        cmd['examples'].append(example)
        dictionary.update_command(args.id, examples=cmd['examples'])
    
    else:
        parser.print_help()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 