#!/usr/bin/env python3
"""
GitIngest Return Format Documentation
===================================

This document demonstrates the exact format returned by the GitIngest library
and our GitIngestTool wrapper.
"""

import sys
import os
import json

# Add the backend directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from gitingest_tool import GitIngestTool


def demonstrate_return_format():
    """Demonstrate and document the exact return format."""
    
    print("="*80)
    print(" GitIngest Return Format Documentation ".center(80, "="))
    print("="*80)
    
    print("\n📋 RETURN FORMAT STRUCTURE:")
    print("-" * 50)
    
    # Test with a simple repository
    tool = GitIngestTool()
    result = tool.analyze_repository("https://github.com/octocat/Hello-World")
    
    if result["success"]:
        print("✅ Successfully analyzed repository!")
        print("\n🔍 COMPLETE RETURN STRUCTURE:")
        print("-" * 40)
        
        # Show the complete structure
        for key, value in result.items():
            if key == "content":
                print(f"'{key}': <string of {len(value)} characters>")
            elif key in ["summary", "tree"]:
                print(f"'{key}': <string of {len(value)} characters>")
            else:
                print(f"'{key}': {repr(value)}")
        
        print("\n📊 DETAILED BREAKDOWN:")
        print("-" * 40)
        
        # 1. SUCCESS FLAG
        print(f"\n1. SUCCESS FLAG:")
        print(f"   Type: {type(result['success'])}")
        print(f"   Value: {result['success']}")
        print(f"   Purpose: Indicates if the analysis was successful")
        
        # 2. REPO URL
        print(f"\n2. REPOSITORY URL:")
        print(f"   Type: {type(result['repo_url'])}")
        print(f"   Value: {result['repo_url']}")
        print(f"   Purpose: The URL of the analyzed repository")
        
        # 3. SUMMARY
        print(f"\n3. SUMMARY:")
        print(f"   Type: {type(result['summary'])}")
        print(f"   Length: {len(result['summary'])} characters")
        print(f"   Content: {repr(result['summary'])}")
        print(f"   Purpose: Repository metadata and statistics")
        
        # 4. TREE
        print(f"\n4. TREE STRUCTURE:")
        print(f"   Type: {type(result['tree'])}")
        print(f"   Length: {len(result['tree'])} characters")
        print(f"   Content: {repr(result['tree'])}")
        print(f"   Purpose: Directory and file structure visualization")
        
        # 5. CONTENT
        print(f"\n5. CONTENT:")
        print(f"   Type: {type(result['content'])}")
        print(f"   Length: {len(result['content'])} characters")
        print(f"   Content preview: {repr(result['content'][:100])}...")
        print(f"   Purpose: Complete file contents with headers")
        
        # 6. ERROR
        print(f"\n6. ERROR:")
        print(f"   Type: {type(result['error'])}")
        print(f"   Value: {result['error']}")
        print(f"   Purpose: Error message if analysis fails (None on success)")
        
        print("\n📄 CONTENT FORMAT DETAILS:")
        print("-" * 40)
        
        # Analyze content structure
        content = result["content"]
        lines = content.split('\n')
        
        print(f"   Total lines: {len(lines)}")
        print(f"   File separator pattern: {'=' * 48}")
        print(f"   File header format: 'FILE: <filename>'")
        print(f"   Structure:")
        for i, line in enumerate(lines[:10]):  # Show first 10 lines
            print(f"     Line {i+1}: {repr(line)}")
        
        # Save complete examples
        print("\n💾 SAVING COMPLETE EXAMPLES:")
        print("-" * 40)
        
        # Save formatted example
        example_data = {
            "format_documentation": {
                "description": "GitIngest tool return format",
                "structure": {
                    "success": {
                        "type": "boolean",
                        "description": "True if analysis succeeded, False otherwise"
                    },
                    "repo_url": {
                        "type": "string", 
                        "description": "The repository URL that was analyzed"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Repository metadata including name, commit, file count, and token estimate"
                    },
                    "tree": {
                        "type": "string",
                        "description": "Directory structure visualization as text tree"
                    },
                    "content": {
                        "type": "string", 
                        "description": "Complete repository content with file separators and headers"
                    },
                    "error": {
                        "type": "string or null",
                        "description": "Error message if analysis failed, null on success"
                    }
                }
            },
            "actual_example": result
        }
        
        with open("/tmp/gitingest_format_documentation.json", "w") as f:
            # Truncate content for readability
            example_copy = example_data.copy()
            if len(example_copy["actual_example"]["content"]) > 500:
                example_copy["actual_example"]["content"] = example_copy["actual_example"]["content"][:500] + "\n...[TRUNCATED FOR DOCUMENTATION]"
            json.dump(example_copy, f, indent=2)
        
        print("   ✅ Complete documentation saved to: /tmp/gitingest_format_documentation.json")
        
        print("\n🎯 KEY INSIGHTS:")
        print("-" * 40)
        print("   1. Return type is always a Python dictionary")
        print("   2. All content fields (summary, tree, content) are plain strings")
        print("   3. Content includes complete file contents with clear separators")
        print("   4. Tree provides a visual directory structure")
        print("   5. Summary gives quick repository statistics")
        print("   6. Error handling is consistent with success/error pattern")
        print("   7. Repository is temporarily cloned, processed, then cleaned up")
        
        print("\n🔧 USAGE PATTERNS:")
        print("-" * 40)
        print("   # Check success first")
        print("   if result['success']:")
        print("       summary = result['summary']")
        print("       tree = result['tree']") 
        print("       content = result['content']")
        print("   else:")
        print("       error = result['error']")
        
    else:
        print(f"❌ Analysis failed: {result['error']}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    demonstrate_return_format()
