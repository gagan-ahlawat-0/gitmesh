"""
Tool Command Filter Service

Filters out tool commands from AI responses and prevents tool command exposure
based on the current mode (default vs PR mode).

SECURITY: This service ensures no tool commands are exposed to users in default mode,
preventing any potential security vulnerabilities from tool command exposure.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class OperationMode(str, Enum):
    """Operation modes for the system."""
    DEFAULT = "default"
    PR_MODE = "pr_mode"

class ToolCommandType(str, Enum):
    """Types of tool commands that need filtering."""
    REPLACE_COMMAND = "replace_command"
    SEARCH_COMMAND = "search_command"
    FILE_OPERATION = "file_operation"
    SYSTEM_COMMAND = "system_command"
    EDIT_COMMAND = "edit_command"

@dataclass
class ToolCommandMatch:
    """A detected tool command in text."""
    original_text: str
    command_type: ToolCommandType
    start_pos: int
    end_pos: int
    suggested_alternative: str

@dataclass
class FilterResult:
    """Result of tool command filtering."""
    filtered_content: str
    commands_filtered: List[ToolCommandMatch]
    alternatives_suggested: int
    security_notes_added: int

class ModeManager:
    """Manages operation modes and permissions."""
    
    def __init__(self):
        """Initialize the mode manager."""
        self._current_mode = OperationMode.DEFAULT
        self._mode_permissions = self._initialize_permissions()
        logger.info("ModeManager initialized in DEFAULT mode")
    
    def _initialize_permissions(self) -> Dict[OperationMode, Set[ToolCommandType]]:
        """Initialize permissions for each mode."""
        return {
            OperationMode.DEFAULT: set(),  # No tool commands allowed in default mode
            OperationMode.PR_MODE: {
                ToolCommandType.REPLACE_COMMAND,
                ToolCommandType.EDIT_COMMAND,
                ToolCommandType.FILE_OPERATION
            }
        }
    
    def set_mode(self, mode: OperationMode) -> None:
        """Set the current operation mode."""
        self._current_mode = mode
        logger.info(f"Mode changed to: {mode}")
    
    def get_current_mode(self) -> OperationMode:
        """Get the current operation mode."""
        return self._current_mode
    
    def is_command_allowed(self, command_type: ToolCommandType) -> bool:
        """Check if a command type is allowed in the current mode."""
        allowed_commands = self._mode_permissions.get(self._current_mode, set())
        return command_type in allowed_commands
    
    def get_allowed_commands(self) -> Set[ToolCommandType]:
        """Get all allowed command types for the current mode."""
        return self._mode_permissions.get(self._current_mode, set())

class ResponseSanitizer:
    """Sanitizes responses by cleaning up filtered content."""
    
    def __init__(self):
        """Initialize the response sanitizer."""
        self.logger = logging.getLogger(__name__)
    
    def sanitize_search_operations(self, content: str) -> str:
        """Replace search operation text with clean status messages."""
        # Replace search commands with user-friendly status messages
        
        # Handle different variations of search commands with context-aware replacements
        search_patterns = [
            (r'>>>\s*search(?:ing)?\s+for\s+([^\n]+)', r'Searching for \1...'),
            (r'>>>\s*search(?:ing)?\s+([^\n]+)', r'Searching \1...'),
            (r'>>>\s*search(?:ing)?\b[^\n]*files?[^\n]*', 'Analyzing files...'),
            (r'>>>\s*search(?:ing)?\b[^\n]*code[^\n]*', 'Analyzing code...'),
            (r'>>>\s*search(?:ing)?\b[^\n]*cache[^\n]*', 'Checking cache...'),
            (r'>>>\s*search(?:ing)?\b[^\n]*repository[^\n]*', 'Mapping codebase...'),
            (r'>>>\s*search(?:ing)?\b[^\n]*', 'Processing request...'),
        ]
        
        for pattern, replacement in search_patterns:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE | re.MULTILINE)
        
        # Clean up multiple spaces and empty lines
        content = re.sub(r'  +', ' ', content)
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        return content.strip()
    
    def clean_response(self, content: str) -> str:
        """Clean response content by removing empty elements and formatting."""
        # Remove empty code blocks
        content = re.sub(r'```\w*\s*\n\s*\n\s*```', '', content)
        content = re.sub(r'```\w*\s*\n\s*```', '', content)
        
        # Remove empty inline code
        content = re.sub(r'``', '', content)
        content = re.sub(r'`\s*`', '', content)
        
        # Clean up multiple consecutive newlines
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        # Remove lines that are just whitespace after filtering
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not re.match(r'^[`\s]*$', stripped):
                cleaned_lines.append(line.rstrip())
            elif not stripped and cleaned_lines and cleaned_lines[-1].strip():
                # Keep empty lines that separate content
                cleaned_lines.append('')
        
        return '\n'.join(cleaned_lines).strip()

class ToolCommandFilter:
    """Service for filtering tool commands from AI responses."""
    
    def __init__(self, mode_manager: Optional[ModeManager] = None):
        """Initialize the tool command filter."""
        self.mode_manager = mode_manager or ModeManager()
        self.response_sanitizer = ResponseSanitizer()
        self.tool_patterns = self._initialize_tool_patterns()
        self.alternative_suggestions = self._initialize_alternatives()
        logger.info("ToolCommandFilter initialized with security filtering enabled")
    
    def _initialize_tool_patterns(self) -> Dict[ToolCommandType, List[str]]:
        """Initialize regex patterns for detecting tool commands."""
        return {
            ToolCommandType.REPLACE_COMMAND: [
                # Process block patterns first (more specific)
                r'<<<<<<< SEARCH.*?>>>>>>> REPLACE',
                r'<<<<<<< ORIGINAL.*?>>>>>>> UPDATED',
                # Then process simple patterns
                r'>>>\s*replace\b[^\n]*',
                r'>>>\s*REPLACE\b[^\n]*',
            ],
            ToolCommandType.SEARCH_COMMAND: [
                r'>>>\s*search\b[^\n]*',
                r'>>>\s*Search\b[^\n]*',
                r'>>>\s*searching\b[^\n]*',
                r'>>>\s*Searching\b[^\n]*',
            ],
            ToolCommandType.FILE_OPERATION: [
                r'>>>\s*file\b[^\n]*',
                r'>>>\s*FILE\b[^\n]*',
                r'>>>\s*read\b[^\n]*',
                r'>>>\s*write\b[^\n]*',
                r'>>>\s*create\b[^\n]*',
                r'>>>\s*delete\b[^\n]*',
            ],
            ToolCommandType.SYSTEM_COMMAND: [
                r'>>>\s*system\b[^\n]*',
                r'>>>\s*SYSTEM\b[^\n]*',
                r'>>>\s*exec\b[^\n]*',
                r'>>>\s*execute\b[^\n]*',
            ],
            ToolCommandType.EDIT_COMMAND: [
                r'>>>\s*edit\b[^\n]*',
                r'>>>\s*EDIT\b[^\n]*',
                r'>>>\s*modify\b[^\n]*',
                r'>>>\s*update\b[^\n]*',
            ]
        }
    
    def _initialize_alternatives(self) -> Dict[ToolCommandType, str]:
        """Initialize alternative suggestions for different command types."""
        return {
            ToolCommandType.REPLACE_COMMAND: "File modifications are not available in this mode.",
            ToolCommandType.SEARCH_COMMAND: "",  # Search operations are cleaned silently
            ToolCommandType.FILE_OPERATION: "File operations are not available in this mode.",
            ToolCommandType.SYSTEM_COMMAND: "System commands are not available in this mode.",
            ToolCommandType.EDIT_COMMAND: "Edit operations are not available in this mode."
        }
    
    def filter_response(self, response: str, mode: Optional[str] = None) -> FilterResult:
        """Filter tool commands from response content.
        
        Args:
            response: Original response content
            mode: Optional mode override (default uses current mode)
            
        Returns:
            FilterResult with filtered content and metadata
        """
        if mode:
            # Temporarily set mode if provided
            original_mode = self.mode_manager.get_current_mode()
            try:
                self.mode_manager.set_mode(OperationMode(mode))
            except ValueError:
                logger.warning(f"Invalid mode provided: {mode}, using current mode")
        
        try:
            filtered_content = response
            commands_filtered = []
            alternatives_suggested = 0
            security_notes_added = 0
            
            # Process each command type
            for command_type, patterns in self.tool_patterns.items():
                if not self.mode_manager.is_command_allowed(command_type):
                    # Filter out this command type
                    for pattern in patterns:
                        matches = list(re.finditer(pattern, filtered_content, re.DOTALL | re.IGNORECASE))
                        for match in reversed(matches):  # Process in reverse to maintain positions
                            original_text = match.group(0)
                            alternative = self.alternative_suggestions.get(command_type, "")
                            
                            # Create match record
                            command_match = ToolCommandMatch(
                                original_text=original_text,
                                command_type=command_type,
                                start_pos=match.start(),
                                end_pos=match.end(),
                                suggested_alternative=alternative
                            )
                            commands_filtered.append(command_match)
                            
                            # Replace with alternative or remove
                            if alternative:
                                filtered_content = (
                                    filtered_content[:match.start()] + 
                                    alternative + 
                                    filtered_content[match.end():]
                                )
                                alternatives_suggested += 1
                            else:
                                # Remove the command entirely
                                filtered_content = (
                                    filtered_content[:match.start()] + 
                                    filtered_content[match.end():]
                                )
            
            # Apply response sanitization
            filtered_content = self.response_sanitizer.sanitize_search_operations(filtered_content)
            filtered_content = self.response_sanitizer.clean_response(filtered_content)
            
            # Add security note if commands were filtered
            if commands_filtered and self.mode_manager.get_current_mode() == OperationMode.DEFAULT:
                security_note = "\n\n*Note: Some tool commands have been filtered for security in default mode.*"
                filtered_content += security_note
                security_notes_added = 1
            
            result = FilterResult(
                filtered_content=filtered_content,
                commands_filtered=commands_filtered,
                alternatives_suggested=alternatives_suggested,
                security_notes_added=security_notes_added
            )
            
            if commands_filtered:
                logger.info(f"Filtered {len(commands_filtered)} tool commands in {self.mode_manager.get_current_mode()} mode")
            
            return result
            
        finally:
            # Restore original mode if it was temporarily changed
            if mode:
                self.mode_manager.set_mode(original_mode)
    
    def is_tool_command_allowed(self, command: str, mode: Optional[str] = None) -> bool:
        """Check if a specific tool command is allowed in the given mode.
        
        Args:
            command: The command to check
            mode: Optional mode override
            
        Returns:
            True if command is allowed, False otherwise
        """
        if mode:
            try:
                check_mode = OperationMode(mode)
            except ValueError:
                check_mode = self.mode_manager.get_current_mode()
        else:
            check_mode = self.mode_manager.get_current_mode()
        
        # Determine command type
        command_type = self._get_command_type(command)
        if not command_type:
            return True  # Unknown commands are allowed by default
        
        # Check if command type is allowed in the mode
        allowed_commands = self.mode_manager._mode_permissions.get(check_mode, set())
        return command_type in allowed_commands
    
    def _get_command_type(self, command: str) -> Optional[ToolCommandType]:
        """Identify the type of a tool command.
        
        Args:
            command: Command to analyze
            
        Returns:
            ToolCommandType if identified, None otherwise
        """
        for command_type, patterns in self.tool_patterns.items():
            for pattern in patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return command_type
        return None
    
    def sanitize_search_operations(self, response: str) -> str:
        """Sanitize search operations in response.
        
        Args:
            response: Response content
            
        Returns:
            Sanitized response with clean search animations
        """
        return self.response_sanitizer.sanitize_search_operations(response)
    
    def get_filter_stats(self) -> Dict[str, any]:
        """Get statistics about filtering operations."""
        return {
            "current_mode": self.mode_manager.get_current_mode().value,
            "allowed_commands": [cmd.value for cmd in self.mode_manager.get_allowed_commands()],
            "total_command_types": len(self.tool_patterns),
            "total_patterns": sum(len(patterns) for patterns in self.tool_patterns.values())
        }

# Global instance
tool_command_filter = ToolCommandFilter()

# Convenience functions
def filter_tool_commands(content: str, mode: Optional[str] = None) -> str:
    """Filter tool commands from content and return filtered text.
    
    Args:
        content: Original content
        mode: Optional mode override
        
    Returns:
        Filtered content with tool commands removed/replaced
    """
    result = tool_command_filter.filter_response(content, mode)
    return result.filtered_content

def is_tool_command_allowed(command: str, mode: Optional[str] = None) -> bool:
    """Check if a tool command is allowed in the given mode.
    
    Args:
        command: Command to check
        mode: Optional mode override
        
    Returns:
        True if command is allowed
    """
    return tool_command_filter.is_tool_command_allowed(command, mode)

def set_operation_mode(mode: str) -> None:
    """Set the global operation mode.
    
    Args:
        mode: Mode to set ("default" or "pr_mode")
    """
    try:
        tool_command_filter.mode_manager.set_mode(OperationMode(mode))
    except ValueError:
        logger.error(f"Invalid mode: {mode}")

def get_current_mode() -> str:
    """Get the current operation mode.
    
    Returns:
        Current mode as string
    """
    return tool_command_filter.mode_manager.get_current_mode().value