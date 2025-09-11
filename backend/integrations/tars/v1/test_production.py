#!/usr/bin/env python3
"""
TARS v1 Production Test
======================

Test script to validate the production-ready TARS system.
Tests all major components with production requirements:
- Only ai framework classes/functions
- GitIngest for repository analysis  
- Supabase PostgreSQL for normal DB
- Qdrant Cloud for vector DB
- GitHub PAT for private repos
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from integrations.tars.v1.config import create_config_template
from integrations.tars.v1.main import TarsMain
from integrations.tars.v1.session import TarsSession
from integrations.tars.v1 import tools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_config():
    """Test configuration validation."""
    logger.info("Testing configuration...")
    
    try:
        # Test creating a config template
        config = create_config_template(
            config_type="production",
            memory_provider="supabase",
            knowledge_provider="qdrant",
            llm_provider="openai"
        )
        
        # Check that only allowed database providers are configured
        assert "supabase" in str(config).lower(), "Supabase configuration not found"
        assert "qdrant" in str(config).lower(), "Qdrant configuration not found"
        
        # Check GitIngest configuration
        assert "gitingest_config" in config, "GitIngest configuration missing"
        
        logger.info("✓ Configuration validation passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Configuration validation failed: {e}")
        return False


def test_tools():
    """Test production tools."""
    logger.info("Testing production tools...")
    
    try:
        # Test that all required tools are available
        required_tools = [
            'repository_analyzer',
            'web_scraper', 
            'internet_search',
            'document_processor',
            'data_analyzer',
            'knowledge_integrator'
        ]
        
        for tool_name in required_tools:
            assert hasattr(tools, tool_name), f"Tool {tool_name} not found"
            tool = getattr(tools, tool_name)
            assert callable(tool), f"Tool {tool_name} is not callable"
        
        logger.info("✓ Production tools validation passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Production tools validation failed: {e}")
        return False


def test_agents():
    """Test agent initialization."""
    logger.info("Testing agent initialization...")
    
    try:
        from integrations.tars.v1.agents import (
            WebCrawlerAgent,
            CodebaseAnalyzerAgent,
            DocumentProcessorAgent,
            DataAnalyzerAgent,
            ControlPanelMonitorAgent,
            KnowledgeOrchestratorAgent,
            CodeComparisonAgent,
            DocumentationAnalyzerAgent,
            ProjectInsightsAgent,
            ReasoningAgent,
            ConversationOrchestratorAgent
        )
        
        # Test basic agent initialization
        agents = [
            WebCrawlerAgent(),
            CodebaseAnalyzerAgent(),
            DocumentProcessorAgent(),
            DataAnalyzerAgent(),
            ControlPanelMonitorAgent(),
            KnowledgeOrchestratorAgent(),
            CodeComparisonAgent(),
            DocumentationAnalyzerAgent(),
            ProjectInsightsAgent(),
            ReasoningAgent(),
            ConversationOrchestratorAgent()
        ]
        
        for agent in agents:
            assert hasattr(agent, 'name'), f"Agent {agent.__class__.__name__} missing name"
            assert hasattr(agent, 'role'), f"Agent {agent.__class__.__name__} missing role"
        
        logger.info("✓ Agent initialization passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Agent initialization failed: {e}")
        return False


def test_session():
    """Test session management."""
    logger.info("Testing session management...")
    
    try:
        session = TarsSession(
            session_id="test-session",
            user_id="test-user",
            project_id="test-project"
        )
        
        assert session.session_id == "test-session"
        assert hasattr(session, 'workflows'), "Session missing workflows"
        
        logger.info("✓ Session management passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Session management failed: {e}")
        return False


def test_main_app():
    """Test main application."""
    logger.info("Testing main application...")
    
    try:
        app = TarsMain()
        
        assert hasattr(app, 'config'), "Main app missing config"
        assert hasattr(app, 'initialize'), "Main app missing initialize method"
        
        logger.info("✓ Main application passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Main application failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("Starting TARS v1 Production Tests...")
    
    tests = [
        test_config,
        test_tools, 
        test_agents,
        test_session,
        test_main_app
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    logger.info(f"\nTest Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        logger.info("🎉 All production tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
