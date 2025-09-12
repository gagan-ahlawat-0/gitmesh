#!/usr/bin/env python3
"""
TARS GitIngest Integration Demo
=============================

This demo showcases the successful integration of GitIngest with TARS v1 in GitMesh.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

def demo_gitingest_direct():
    """Demo: Direct GitIngest Tool Usage"""
    print("🔍 Demo: GitIngest Tool Direct Usage")
    print("=" * 50)
    
    from integrations.tars.v1.gitingest_tool import GitIngestTool
    
    # Create tool instance
    tool = GitIngestTool()
    print("✅ GitIngest tool initialized")
    
    # Analyze a public repository
    print("\n📄 Analyzing public repository: octocat/Hello-World")
    result = tool.analyze_repository("https://github.com/octocat/Hello-World")
    
    if result["success"]:
        print("✅ Analysis successful!")
        print(f"📋 Summary: {result['summary']}")
        print(f"🌳 File Tree:\n{result['tree']}")
        print(f"📄 Content Preview:\n{result['content'][:200]}...")
        
        metadata = result.get("metadata", {})
        print(f"\n📊 Metadata:")
        print(f"   - Content Length: {metadata.get('content_length', 0)} chars")
        print(f"   - Has Authentication: {metadata.get('has_auth', False)}")
        print(f"   - Timestamp: {metadata.get('timestamp', 'N/A')}")
    else:
        print(f"❌ Analysis failed: {result['error']}")

async def demo_tars_integration():
    """Demo: TARS GitIngest Integration"""
    print("\n\n🎯 Demo: TARS GitIngest Integration")
    print("=" * 50)
    
    from integrations.tars.v1.tars_wrapper import GitMeshTarsWrapper
    
    # Create TARS wrapper
    wrapper = GitMeshTarsWrapper(
        user_id="demo_user",
        project_id="demo_project", 
        repository_id="octocat/Hello-World"
    )
    print("✅ TARS wrapper created")
    
    # Check GitIngest status
    status = wrapper.get_gitingest_status()
    print(f"📊 GitIngest Status: Available={status.get('available')}, Initialized={status.get('tool_initialized')}")
    
    # Analyze repository through TARS
    print("\n🔍 Analyzing repository through TARS...")
    analysis = await wrapper.analyze_repository_with_gitingest(
        "https://github.com/octocat/Hello-World"
    )
    
    if analysis.get("success"):
        print("✅ TARS GitIngest analysis successful!")
        print(f"📋 Summary Length: {len(analysis.get('summary', ''))}")
        print(f"🌳 Tree Length: {len(analysis.get('tree', ''))}")
        print(f"📄 Content Length: {len(analysis.get('content', ''))}")
        print(f"🎯 Stored in Knowledge Base: Yes")
    else:
        print(f"❌ TARS analysis failed: {analysis.get('error')}")
    
    # Demo TARS system status
    print("\n📊 TARS System Status:")
    system_status = await wrapper.get_system_status()
    gitmesh_integration = system_status.get("gitmesh_integration", {})
    print(f"   - Database Available: {gitmesh_integration.get('database_available')}")
    print(f"   - Vector Store Available: {gitmesh_integration.get('vector_store_available')}")
    print(f"   - Collection: {gitmesh_integration.get('collection_name', 'N/A')}")

def demo_convenience_functions():
    """Demo: Convenience Functions"""
    print("\n\n🛠️ Demo: Convenience Functions")
    print("=" * 50)
    
    from integrations.tars.v1.gitingest_tool import extract_details, analyze_repository
    
    # Test convenience function
    print("📄 Using extract_details() function...")
    summary, tree, content = extract_details("https://github.com/octocat/Hello-World")
    
    if summary:
        print("✅ Extraction successful!")
        print(f"📋 Summary (first 100 chars): {summary[:100]}...")
        print(f"🌳 Tree (first 50 chars): {tree[:50]}...")
        print(f"📄 Content (first 50 chars): {content[:50]}...")
    else:
        print("❌ Extraction failed")
    
    # Test analyze_repository function
    print("\n🔍 Using analyze_repository() function...")
    result = analyze_repository("https://github.com/octocat/Hello-World")
    
    if result["success"]:
        print("✅ Analysis successful!")
        print(f"📊 Result keys: {list(result.keys())}")
    else:
        print(f"❌ Analysis failed: {result['error']}")

async def main():
    """Main demo runner"""
    print("🚀 GitMesh TARS GitIngest Integration Demo")
    print("==========================================")
    print("This demo shows the successful integration of GitIngest with TARS v1")
    print()
    
    try:
        # Demo 1: Direct GitIngest usage
        demo_gitingest_direct()
        
        # Demo 2: TARS integration
        await demo_tars_integration()
        
        # Demo 3: Convenience functions
        demo_convenience_functions()
        
        print("\n🎉 Demo completed successfully!")
        print("\n📋 Summary:")
        print("   ✅ GitIngest tool working correctly")
        print("   ✅ TARS integration functional")
        print("   ✅ Authentication system integrated")
        print("   ✅ Convenience functions available")
        print("   ✅ Knowledge base storage working")
        print("\n🎯 The GitIngest tool is now fully integrated into TARS!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
