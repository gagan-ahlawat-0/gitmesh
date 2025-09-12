#!/usr/bin/env python3
"""
Test script to understand GitIngest return format
===============================================
"""

import json
import sys
import os

# Add the backend directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from gitingest_tool import GitIngestTool, extract_details, analyze_repository


def print_separator(title):
    """Print a nice separator with title."""
    print("\n" + "="*80)
    print(f" {title} ".center(80, "="))
    print("="*80)


def analyze_format_detailed(result):
    """Analyze the detailed format of the result."""
    print(f"📊 Result Type: {type(result)}")
    print(f"📊 Result Keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
    
    if result.get("success"):
        print("\n🔍 Analyzing each component:")
        
        # Summary analysis
        summary = result.get("summary", "")
        print(f"\n📋 SUMMARY:")
        print(f"   Type: {type(summary)}")
        print(f"   Length: {len(summary)} characters")
        print(f"   First 300 chars: {summary[:300]}...")
        
        # Tree analysis
        tree = result.get("tree", "")
        print(f"\n🌳 TREE:")
        print(f"   Type: {type(tree)}")
        print(f"   Length: {len(tree)} characters")
        print(f"   First 300 chars: {tree[:300]}...")
        
        # Content analysis
        content = result.get("content", "")
        print(f"\n📄 CONTENT:")
        print(f"   Type: {type(content)}")
        print(f"   Length: {len(content)} characters")
        print(f"   First 300 chars: {content[:300]}...")
        
        # Look for patterns in the content
        print(f"\n🔍 Content Analysis:")
        print(f"   Lines count: {content.count(chr(10)) + 1}")
        print(f"   Contains 'README': {'README' in content}")
        print(f"   Contains 'package.json': {'package.json' in content}")
        print(f"   Contains 'src/': {'src/' in content}")
        print(f"   Contains '```': {'```' in content}")
    else:
        print(f"❌ Error: {result.get('error')}")


def test_small_repo():
    """Test with a smaller repository to understand the format."""
    print_separator("TESTING SMALL REPOSITORY")
    
    # Use a smaller repository for testing
    small_repo = "https://github.com/octocat/Hello-World"
    
    tool = GitIngestTool()
    result = tool.analyze_repository(small_repo)
    
    analyze_format_detailed(result)
    
    return result


def test_convenience_functions():
    """Test the convenience functions."""
    print_separator("TESTING CONVENIENCE FUNCTIONS")
    
    repo_url = "https://github.com/octocat/Hello-World"
    
    print("🔧 Testing extract_details function...")
    summary, tree, content = extract_details(repo_url)
    
    print(f"📋 Summary (extract_details):")
    print(f"   Type: {type(summary)}, Length: {len(summary)}")
    print(f"   Content: {summary[:200]}...")
    
    print(f"\n🌳 Tree (extract_details):")
    print(f"   Type: {type(tree)}, Length: {len(tree)}")
    print(f"   Content: {tree[:200]}...")
    
    print(f"\n📄 Content (extract_details):")
    print(f"   Type: {type(content)}, Length: {len(content)}")
    print(f"   Content: {content[:200]}...")


def test_individual_methods():
    """Test individual getter methods."""
    print_separator("TESTING INDIVIDUAL METHODS")
    
    repo_url = "https://github.com/octocat/Hello-World"
    tool = GitIngestTool()
    
    print("🔧 Testing individual getter methods...")
    
    summary = tool.get_summary(repo_url)
    print(f"📋 get_summary(): {type(summary)}, Length: {len(summary) if summary else 0}")
    if summary:
        print(f"   Content: {summary[:200]}...")
    
    tree = tool.get_tree(repo_url)
    print(f"\n🌳 get_tree(): {type(tree)}, Length: {len(tree) if tree else 0}")
    if tree:
        print(f"   Content: {tree[:200]}...")
    
    content = tool.get_content(repo_url)
    print(f"\n📄 get_content(): {type(content)}, Length: {len(content) if content else 0}")
    if content:
        print(f"   Content: {content[:200]}...")


def save_sample_output():
    """Save a sample output to file for inspection."""
    print_separator("SAVING SAMPLE OUTPUT")
    
    repo_url = "https://github.com/octocat/Hello-World"
    tool = GitIngestTool()
    result = tool.analyze_repository(repo_url)
    
    if result.get("success"):
        # Save each component to separate files
        with open("/tmp/gitingest_sample_summary.txt", "w") as f:
            f.write(result["summary"])
        
        with open("/tmp/gitingest_sample_tree.txt", "w") as f:
            f.write(result["tree"])
        
        with open("/tmp/gitingest_sample_content.txt", "w") as f:
            f.write(result["content"])
        
        # Save the full result as JSON (excluding content for readability)
        result_copy = result.copy()
        result_copy["content"] = f"[CONTENT TRUNCATED - {len(result['content'])} chars]"
        result_copy["summary"] = f"[SUMMARY TRUNCATED - {len(result['summary'])} chars]"
        result_copy["tree"] = f"[TREE TRUNCATED - {len(result['tree'])} chars]"
        
        with open("/tmp/gitingest_sample_result.json", "w") as f:
            json.dump(result_copy, f, indent=2)
        
        print("✅ Sample output saved to:")
        print("   📋 /tmp/gitingest_sample_summary.txt")
        print("   🌳 /tmp/gitingest_sample_tree.txt")
        print("   📄 /tmp/gitingest_sample_content.txt")
        print("   📊 /tmp/gitingest_sample_result.json")


def main():
    """Main test function."""
    print("🚀 GitIngest Format Analysis Tool")
    print("=" * 80)
    
    # Test 1: Detailed analysis of result format
    result = test_small_repo()
    
    # Test 2: Convenience functions
    test_convenience_functions()
    
    # Test 3: Individual methods
    test_individual_methods()
    
    # Test 4: Save sample output
    save_sample_output()
    
    print_separator("SUMMARY")
    print("🎯 Key Findings:")
    print("   1. GitIngest returns a dictionary with 'success', 'summary', 'tree', 'content' keys")
    print("   2. All text fields are strings")
    print("   3. Content includes the full repository analysis")
    print("   4. Tree shows the file structure")
    print("   5. Summary provides metadata and statistics")
    print("\n✅ Test completed! Check the sample files in /tmp/ for detailed examples.")


if __name__ == "__main__":
    main()
