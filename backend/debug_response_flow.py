#!/usr/bin/env python3
"""
Debug script to trace the response processing flow
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from services.response_processor import ResponseProcessor

def debug_specific_response():
    """Debug the specific response that's not working"""
    processor = ResponseProcessor()
    
    # The exact response you mentioned
    ai_response = """To answer your question about the temperature threshold, I'll need to see the relevant code. Please search your repository for `trigger_violation` and add the file(s) that contain this logic to our chat. Based on the file structure, they might be located within the `app/` directory, or a `lib/`, `utils/` or `components/` directory."""
    
    print("Debugging Specific Response")
    print("=" * 60)
    print(f"Response: {ai_response}")
    print("\n" + "=" * 60)
    
    # Test each pattern individually
    patterns = [
        (r'(?:please\s+|could\s+you\s+(?:please\s+)?)?add\s+(?:the\s+)?(?:file\s+)?[`"]?([a-zA-Z0-9_/.-]+(?:\.[a-zA-Z0-9]+)?)[`"]?\s+to\s+(?:the\s+)?(?:chat|context)', "Pattern 1: Add file to chat"),
        (r'(?:i\s+)?(?:need|want)\s+to\s+(?:see|look\s+at|examine)\s+(?:the\s+)?(?:contents?\s+of\s+)?[`"]?([a-zA-Z0-9_/.-]+(?:\.[a-zA-Z0-9]+)?)[`"]?', "Pattern 2: Need to see"),
        (r'(?:can\s+you\s+|could\s+you\s+)?show\s+me\s+(?:the\s+)?[`"]?([a-zA-Z0-9_/.-]+(?:\.[a-zA-Z0-9]+)?)[`"]?\s+(?:file|so)', "Pattern 3: Show me"),
        (r'let\s+me\s+(?:examine|check|look\s+at)\s+(?:the\s+)?(?:database\s+models\s+in\s+)?[`"]?([a-zA-Z0-9_/.-]+(?:\.[a-zA-Z0-9]+)?)[`"]?', "Pattern 4: Let me examine"),
        (r'(?:file|module|component|script):\s*[`"]?([a-zA-Z0-9_/.-]+(?:\.[a-zA-Z0-9]+)?)[`"]?', "Pattern 5: File reference"),
        (r'(?:would\s+be|start\s+would\s+be)\s+[`"]?([a-zA-Z0-9_/.-]+(?:\.[a-zA-Z0-9]+)?)[`"]?', "Pattern 6: Would be"),
        (r'search\s+(?:your\s+repository\s+)?for\s+[`"]?([a-zA-Z0-9_/.-]+)[`"]?\s+and\s+add\s+(?:the\s+)?file', "Pattern 8: Search and add"),
        (r'add\s+(?:the\s+)?file\(?s?\)?\s+that\s+contain\s+[`"]?([a-zA-Z0-9_/.-]+)[`"]?', "Pattern 9: Add files that contain"),
        (r'they\s+might\s+be\s+located\s+within\s+the\s+[`"]?([a-zA-Z0-9_/.-]+)[`"]?\s+directory', "Pattern 10: Located within directory"),
        (r'please\s+search\s+(?:your\s+repository\s+)?for\s+[`"]?([a-zA-Z0-9_/.-]+)[`"]?', "Pattern 11: Please search"),
    ]
    
    import re
    
    for pattern_str, description in patterns:
        pattern = re.compile(pattern_str, re.IGNORECASE)
        matches = pattern.finditer(ai_response)
        match_found = False
        
        for match in matches:
            match_found = True
            print(f"✅ {description}")
            print(f"   Matched: '{match.group(0)}'")
            print(f"   Captured: '{match.group(1)}'")
            print(f"   Position: {match.start()}-{match.end()}")
        
        if not match_found:
            print(f"❌ {description} - No match")
    
    print("\n" + "=" * 60)
    
    # Now test the full processor
    processed = processor.process_response(ai_response)
    
    print(f"Processor Results:")
    print(f"  File requests found: {len(processed.metadata.get('requested_files', []))}")
    print(f"  Interactive elements: {len(processed.interactive_elements)}")
    
    requested_files = processed.metadata.get('requested_files', [])
    for i, req in enumerate(requested_files, 1):
        print(f"  {i}. {req['path']} - {req['reason'][:50]}...")
    
    # Test if this would create the right metadata structure for frontend
    frontend_metadata = {
        "requested_files": requested_files,
        "file_requests_count": len(requested_files),
        "interactive_elements": [
            {
                "element_type": elem.element_type,
                "label": elem.label,
                "value": elem.value,
                "action": elem.action,
                "metadata": elem.metadata
            }
            for elem in processed.interactive_elements
        ]
    }
    
    print(f"\nFrontend would receive:")
    print(f"  requested_files: {len(frontend_metadata['requested_files'])}")
    print(f"  file_requests_count: {frontend_metadata['file_requests_count']}")
    print(f"  interactive_elements: {len(frontend_metadata['interactive_elements'])}")
    
    return processed

if __name__ == "__main__":
    debug_specific_response()