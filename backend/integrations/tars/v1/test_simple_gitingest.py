#!/usr/bin/env python3
"""
Simple test for TARS GitIngest integration - no async in main thread
"""

import sys
import os
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gitingest_direct():
    """Test GitIngest tool directly without async context."""
    try:
        print("🔍 Testing GitIngest Tool Directly")
        print("=" * 40)
        
        # Import GitIngest tool
        from integrations.tars.v1.gitingest_tool import GitIngestTool
        
        # Create tool instance
        tool = GitIngestTool()
        print("✅ GitIngest tool created successfully")
        
        # Test simple repository analysis
        print("\n📄 Testing repository analysis...")
        result = tool.analyze_repository("https://github.com/octocat/Hello-World")
        
        if result.get("success"):
            print("✅ Repository analysis successful!")
            print(f"📋 Summary length: {len(result.get('summary', ''))}")
            print(f"🌳 Tree length: {len(result.get('tree', ''))}")
            print(f"📄 Content length: {len(result.get('content', ''))}")
            
            # Show sample content
            summary = result.get('summary', '')
            if summary:
                print(f"\n📋 Sample summary:")
                print(f"{summary[:200]}...")
                
        else:
            print(f"❌ Repository analysis failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Test extract_details method
        print("\n🔧 Testing extract_details method...")
        details = tool.extract_details("https://github.com/octocat/Hello-World")
        
        if "error" not in details:
            print("✅ Extract details successful!")
            print(f"📋 Summary: {len(details.get('summary', ''))} chars")
            print(f"🌳 Tree: {len(details.get('tree', ''))} chars")
            print(f"📄 Content: {len(details.get('content', ''))} chars")
        else:
            print(f"❌ Extract details failed: {details.get('error')}")
        
        return True
        
    except Exception as e:
        logger.error(f"Direct GitIngest test failed: {e}")
        print(f"❌ Direct test failed: {e}")
        return False

def test_tars_wrapper_sync():
    """Test TARS wrapper GitIngest integration synchronously."""
    try:
        print("\n🔍 Testing TARS Wrapper (Sync)")
        print("=" * 40)
        
        # Import TARS wrapper
        from integrations.tars.v1.tars_wrapper import GitMeshTarsWrapper
        
        # Create TARS wrapper instance
        wrapper = GitMeshTarsWrapper(
            user_id="test_user",
            project_id="test_project",
            repository_id="octocat/Hello-World",
            branch="main"
        )
        
        print("✅ TARS wrapper created successfully")
        
        # Check GitIngest status
        print("\n📊 Checking GitIngest status...")
        status = wrapper.get_gitingest_status()
        print(f"GitIngest available: {status.get('available', False)}")
        print(f"Tool initialized: {status.get('tool_initialized', False)}")
        
        if not status.get('available'):
            print("❌ GitIngest not available")
            return False
        
        print("✅ GitIngest is available and ready")
        
        # Test direct access to the gitingest tool
        if wrapper.gitingest_tool:
            print("\n🧪 Testing direct tool access...")
            direct_result = wrapper.gitingest_tool.analyze_repository("https://github.com/octocat/Hello-World")
            if direct_result.get("success"):
                print("✅ Direct tool access works!")
                print(f"Summary: {len(direct_result.get('summary', ''))} chars")
            else:
                print(f"❌ Direct tool access failed: {direct_result.get('error')}")
        
        return True
        
    except Exception as e:
        logger.error(f"TARS wrapper test failed: {e}")
        print(f"❌ TARS wrapper test failed: {e}")
        return False

def main():
    """Main test runner."""
    print("🚀 Starting Simple TARS GitIngest Integration Tests")
    
    success_count = 0
    total_tests = 2
    
    # Test 1: Direct GitIngest tool
    if test_gitingest_direct():
        success_count += 1
    
    # Test 2: TARS wrapper (sync only)
    if test_tars_wrapper_sync():
        success_count += 1
    
    print(f"\n📊 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
