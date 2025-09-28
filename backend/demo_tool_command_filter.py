#!/usr/bin/env python3
"""
Demonstration of Tool Command Filter System

This script demonstrates how the tool command filtering system works
in different modes and with various types of tool commands.
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from services.tool_command_filter import (
    filter_tool_commands,
    set_operation_mode,
    get_current_mode,
    is_tool_command_allowed
)

def print_separator(title):
    """Print a section separator."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def demonstrate_filtering(raw_response, mode="default"):
    """Demonstrate filtering for a given response and mode."""
    print(f"\nMode: {mode.upper()}")
    print("-" * 40)
    
    # Set the mode
    set_operation_mode(mode)
    
    print("ORIGINAL RESPONSE:")
    print(raw_response)
    
    print("\nFILTERED RESPONSE:")
    filtered_response = filter_tool_commands(raw_response)
    print(filtered_response)
    
    print(f"\nCurrent mode: {get_current_mode()}")

def main():
    """Main demonstration function."""
    print("Tool Command Filter System Demonstration")
    print("This demonstrates how tool commands are filtered based on operation mode.")
    
    # Example 1: Simple replace command
    print_separator("Example 1: Simple Replace Command")
    
    simple_response = """
    I'll help you fix that bug. Let me make the necessary changes:
    
    >>> replace old_function() with new_function()
    
    The function has been updated successfully!
    """
    
    demonstrate_filtering(simple_response, "default")
    demonstrate_filtering(simple_response, "pr_mode")
    
    # Example 2: Search operations
    print_separator("Example 2: Search Operations")
    
    search_response = """
    Let me search for that information:
    
    >>> search for error patterns in logs
    
    Based on my search, I found the issue in the authentication module.
    """
    
    demonstrate_filtering(search_response, "default")
    demonstrate_filtering(search_response, "pr_mode")
    
    # Example 3: Complex replace blocks
    print_separator("Example 3: Complex Replace Blocks")
    
    complex_response = """
    I'll update the configuration for you:
    
    <<<<<<< SEARCH
    def old_config():
        return {"debug": False}
    =======
    def new_config():
        return {"debug": True, "logging": "info"}
    >>>>>>> REPLACE
    
    Configuration updated successfully!
    """
    
    demonstrate_filtering(complex_response, "default")
    demonstrate_filtering(complex_response, "pr_mode")
    
    # Example 4: Mixed commands
    print_separator("Example 4: Mixed Commands")
    
    mixed_response = """
    I'll help you with multiple operations:
    
    1. First, let me search: >>> search for config files
    2. Then I'll edit the file: >>> edit config.py
    3. Finally, I'll replace the values: >>> replace old_value with new_value
    4. And create a backup: >>> file create backup.py
    
    All operations completed successfully!
    """
    
    demonstrate_filtering(mixed_response, "default")
    demonstrate_filtering(mixed_response, "pr_mode")
    
    # Example 5: Command permission checking
    print_separator("Example 5: Command Permission Checking")
    
    commands_to_check = [
        ">>> replace old with new",
        ">>> search for patterns",
        ">>> edit file.py",
        ">>> file create new.py",
        ">>> system restart"
    ]
    
    for mode in ["default", "pr_mode"]:
        set_operation_mode(mode)
        print(f"\nMode: {mode.upper()}")
        print("-" * 20)
        
        for command in commands_to_check:
            allowed = is_tool_command_allowed(command)
            status = "ALLOWED" if allowed else "BLOCKED"
            print(f"{command:<30} -> {status}")
    
    # Example 6: Real-world chat scenario
    print_separator("Example 6: Real-world Chat Scenario")
    
    chat_response = """
    I'll help you implement the user authentication feature. Let me analyze the codebase first:
    
    >>> search for existing auth implementations
    
    I found some authentication code in the auth module. Now I'll make the necessary updates:
    
    >>> replace authenticate_user(username, password) with authenticate_user(username, password, remember_me=False)
    
    I'll also need to update the login form:
    
    <<<<<<< SEARCH
    <form method="post">
        <input name="username" required>
        <input name="password" type="password" required>
        <button type="submit">Login</button>
    </form>
    =======
    <form method="post">
        <input name="username" required>
        <input name="password" type="password" required>
        <input name="remember_me" type="checkbox"> Remember me
        <button type="submit">Login</button>
    </form>
    >>>>>>> REPLACE
    
    Perfect! The authentication system now supports the "remember me" functionality.
    
    *Analyzed 3 files from your codebase*
    *Referenced files: auth.py, login.html, models.py*
    """
    
    demonstrate_filtering(chat_response, "default")
    demonstrate_filtering(chat_response, "pr_mode")
    
    print_separator("Summary")
    print("""
    Key Features Demonstrated:
    
    1. DEFAULT MODE:
       - All tool commands are filtered for security
       - Search commands are removed silently
       - Replace/edit commands show security messages
       - Security notes are added to responses
    
    2. PR MODE:
       - Replace and edit commands are allowed
       - Search commands are still filtered
       - File operations are permitted
       - System commands remain blocked
    
    3. FILTERING CAPABILITIES:
       - Simple tool commands (>>> replace, >>> search)
       - Complex replace blocks (<<<<<<< SEARCH ... >>>>>>> REPLACE)
       - Mixed command types in single responses
       - Preserves regular content and formatting
       - Maintains response readability
    
    4. SECURITY BENEFITS:
       - Prevents tool command exposure to end users
       - Maintains professional chat experience
       - Provides appropriate alternatives when needed
       - Supports different permission levels
    """)

if __name__ == "__main__":
    main()