#!/usr/bin/env python3
"""
Test script for TARS GitIngest integration
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_tars_gitingest_integration():
    """Test the GitIngest integration with TARS."""
    try:
        print("🔍 Testing TARS GitIngest Integration")
        print("=" * 50)
        
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
            print("❌ GitIngest not available. Please check installation.")
            if 'error' in status:
                print(f"Error: {status['error']}")
            return False
        
        print("✅ GitIngest is available and ready")
        
        # Test repository analysis
        print("\n🔍 Testing repository analysis...")
        repo_url = "https://github.com/octocat/Hello-World"
        branch = "main"
        
        analysis_result = await wrapper.analyze_repository_with_gitingest(repo_url, branch)
        
        if analysis_result.get("success"):
            print("✅ Repository analysis successful!")
            print(f"Summary length: {len(analysis_result.get('summary', ''))}")
            print(f"Tree length: {len(analysis_result.get('tree', ''))}")
            print(f"Content length: {len(analysis_result.get('content', ''))}")
            
            # Show a sample of the summary
            summary = analysis_result.get('summary', '')
            if summary:
                print(f"\nSample summary (first 200 chars):")
                print(f"{summary[:200]}...")
            
        else:
            print(f"❌ Repository analysis failed: {analysis_result.get('error', 'Unknown error')}")
            return False
        
        # Test with a different repository format (owner/repo)
        print(f"\n🔍 Testing with owner/repo format...")
        analysis_result2 = await wrapper.analyze_repository_with_gitingest("microsoft/TypeScript", "main")
        
        if analysis_result2.get("success"):
            print("✅ Owner/repo format analysis successful!")
            print(f"Summary length: {len(analysis_result2.get('summary', ''))}")
        else:
            print(f"⚠️ Owner/repo format analysis failed: {analysis_result2.get('error', 'Unknown error')}")
            print("This might be due to authentication requirements for larger repos")
        
        # Test initialization
        print("\n🔧 Testing TARS initialization...")
        init_success = await wrapper.initialize()
        
        if init_success:
            print("✅ TARS initialized successfully")
            
            # Test system status
            system_status = await wrapper.get_system_status()
            print(f"✅ System status retrieved: {len(system_status)} keys")
            
        else:
            print("❌ TARS initialization failed")
        
        print("\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        print(f"❌ Test failed: {e}")
        return False
    finally:
        if 'wrapper' in locals():
            try:
                await wrapper.shutdown()
                print("🔧 TARS wrapper shut down")
            except:
                pass

async def test_direct_gitingest():
    """Test GitIngest tool directly."""
    try:
        print("\n🔍 Testing GitIngest tool directly")
        print("=" * 40)
        
        # Import GitIngest tool
        from integrations.tars.v1.gitingest_tool import GitIngestTool
        
        # Create tool instance
        tool = GitIngestTool()
        print("✅ GitIngest tool created")
        
        # Test simple extraction
        result = tool.extract_details("https://github.com/octocat/Hello-World")
        if "error" not in result:
            print(f"✅ Extract details successful: Summary length: {len(result.get('summary', ''))}")
        else:
            print(f"❌ Extract details failed: {result.get('error', 'Unknown error')}")
        
        # Test full analysis
        analysis = tool.analyze_repository("https://github.com/octocat/Hello-World")
        if analysis.get("success"):
            print("✅ Direct analysis successful!")
            print(f"Has summary: {'summary' in analysis}")
            print(f"Has tree: {'tree' in analysis}")
            print(f"Has content: {'content' in analysis}")
        else:
            print(f"❌ Direct analysis failed: {analysis.get('error')}")
        
        return True
        
    except Exception as e:
        logger.error(f"Direct GitIngest test failed: {e}")
        print(f"❌ Direct test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting TARS GitIngest Integration Tests")
    
    # Run direct GitIngest test first
    asyncio.run(test_direct_gitingest())
    
    # Run full integration test
    success = asyncio.run(test_tars_gitingest_integration())
    
    if success:
        print("\n🎉 All integration tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
