"""
TARS v1 Configuration Templates
==============================

Configuration templates and utilities for TARS v1.
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path


# Default configurations - Production-ready with Supabase PostgreSQL + Qdrant Cloud
DEFAULT_MEMORY_CONFIGS = {
    "supabase": {
        "provider": "supabase",
        "use_embedding": True,
        "embedding_provider": "sentence_transformers",
        "quality_scoring": True,
        "advanced_memory": True,
        "supabase_url": "${SUPABASE_URL}",
        "supabase_key": "${SUPABASE_ANON_KEY}",
        "supabase_service_key": "${SUPABASE_SERVICE_ROLE_KEY}",
        "connection_config": {
            "url": "${SUPABASE_URL}",
            "key": "${SUPABASE_ANON_KEY}",
            "service_key": "${SUPABASE_SERVICE_ROLE_KEY}"
        }
    }
}

def get_default_model_from_env():
    """Get default model using enhanced model detection from .env"""
    try:
        # Dynamic import to avoid circular dependencies
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from core.context_manager import get_default_model
        model_info = get_default_model()
        return model_info['model']
    except Exception:
        return "gpt-4o-mini"  # final fallback

DEFAULT_LLM_CONFIGS = {
    "default": {
        "model": None,  # Will be set dynamically from .env configuration
        "temperature": 0.7,
        "max_tokens": 4000,
        "stream": True,
        "metrics": True
    },
    
    "openai_turbo": {
        "model": "gpt-3.5-turbo",
        "temperature": 0.7,
        "max_tokens": 2000,
        "stream": True,
        "metrics": True,
        "api_key": "${MODEL_KEY}"
    },
    
    "local_llm": {
        "model": "local",
        "base_url": "http://localhost:11434",
        "model_name": "llama2",
        "temperature": 0.7,
        "max_tokens": 2000,
        "stream": True,
        "metrics": True
    }
}

DEFAULT_KNOWLEDGE_CONFIGS = {
    "qdrant": {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "url": "${QDRANT_URL}",
                "api_key": "${QDRANT_API_KEY}",
                "collection_name": "tars_knowledge"
            }
        },
        "chunking": {
            "strategy": "adaptive",
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "quality_scoring": True
        }
    }
}

WORKFLOW_CONFIGS = {
    "default": {
        "acquisition": {
            "max_concurrent_agents": 4,
            "timeout_seconds": 300,
            "retry_attempts": 3,
            "rate_limit": {
                "requests_per_minute": 60,
                "burst_limit": 10
            }
        },
        "analysis": {
            "max_concurrent_agents": 2,
            "timeout_seconds": 600,
            "deep_analysis": True,
            "generate_summaries": True,
            "cross_reference": True
        },
        "conversation": {
            "max_context_length": 8000,
            "memory_lookback": 10,
            "response_streaming": True,
            "auto_save_session": True
        }
    },
    
    "performance": {
        "acquisition": {
            "max_concurrent_agents": 8,
            "timeout_seconds": 180,
            "retry_attempts": 2,
            "rate_limit": {
                "requests_per_minute": 120,
                "burst_limit": 20
            }
        },
        "analysis": {
            "max_concurrent_agents": 4,
            "timeout_seconds": 300,
            "deep_analysis": False,
            "generate_summaries": True,
            "cross_reference": False
        },
        "conversation": {
            "max_context_length": 4000,
            "memory_lookback": 5,
            "response_streaming": True,
            "auto_save_session": True
        }
    },
    
    "comprehensive": {
        "acquisition": {
            "max_concurrent_agents": 2,
            "timeout_seconds": 600,
            "retry_attempts": 5,
            "rate_limit": {
                "requests_per_minute": 30,
                "burst_limit": 5
            }
        },
        "analysis": {
            "max_concurrent_agents": 1,
            "timeout_seconds": 1200,
            "deep_analysis": True,
            "generate_summaries": True,
            "cross_reference": True,
            "multi_perspective": True
        },
        "conversation": {
            "max_context_length": 12000,
            "memory_lookback": 20,
            "response_streaming": True,
            "auto_save_session": True,
            "context_enhancement": True
        }
    }
}


def create_config_template(
    config_type: str = "default",
    memory_provider: str = "supabase",
    llm_provider: str = "openai",
    knowledge_provider: str = "qdrant",
    workflow_profile: str = "default"
) -> Dict[str, Any]:
    """
    Create a configuration template.
    
    Args:
        config_type: Type of configuration (default, development, production)
        memory_provider: Memory provider (supabase only - production ready)
        llm_provider: LLM provider (openai, local_llm)
        knowledge_provider: Knowledge provider (qdrant only - production ready)
        workflow_profile: Workflow profile (default, performance, comprehensive)
        
    Returns:
        Configuration dictionary
    """
    # Force production-ready providers
    if memory_provider != "supabase":
        print(f"⚠️  Forcing memory provider to 'supabase' (production-ready). Requested: {memory_provider}")
        memory_provider = "supabase"
    
    if knowledge_provider != "qdrant":
        print(f"⚠️  Forcing knowledge provider to 'qdrant' (production-ready). Requested: {knowledge_provider}")
        knowledge_provider = "qdrant"
    
    config = {
        "tars_version": "1.0.0",
        "config_type": config_type,
        "memory_config": DEFAULT_MEMORY_CONFIGS.get(memory_provider, DEFAULT_MEMORY_CONFIGS["supabase"]),
        "llm_config": DEFAULT_LLM_CONFIGS.get(llm_provider, DEFAULT_LLM_CONFIGS["openai"]),
        "knowledge_config": DEFAULT_KNOWLEDGE_CONFIGS.get(knowledge_provider, DEFAULT_KNOWLEDGE_CONFIGS["qdrant"]),
        "workflow_config": WORKFLOW_CONFIGS.get(workflow_profile, WORKFLOW_CONFIGS["default"]),
        "github_config": {
            "personal_access_token": "${GITHUB_PAT}",
            "default_branch": "main"
        },
        "gitingest_config": {
            "use_gitingest": True,
            "max_file_size": 1048576,  # 1MB
            "timeout": 120
        }
    }
    
    # Add environment-specific settings
    if config_type == "development":
        config["debug"] = True
        config["verbose"] = True
        config["telemetry"] = True
        config["memory_config"]["quality_scoring"] = False
        config["workflow_config"]["acquisition"]["max_concurrent_agents"] = 2
        
    elif config_type == "production":
        config["debug"] = False
        config["verbose"] = False
        config["telemetry"] = True
        config["memory_config"]["quality_scoring"] = True
        config["security"] = {
            "rate_limiting": True,
            "input_validation": True,
            "output_filtering": True
        }
        
    elif config_type == "testing":
        config["debug"] = True
        config["verbose"] = True
        config["telemetry"] = False
        # Still use production providers for testing
        config["workflow_config"]["acquisition"]["max_concurrent_agents"] = 1
    
    return config


def save_config_template(
    config: Dict[str, Any],
    output_path: str,
    create_dirs: bool = True
) -> bool:
    """
    Save a configuration template to file.
    
    Args:
        config: Configuration dictionary
        output_path: Path to save the configuration
        create_dirs: Create directories if they don't exist
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if create_dirs:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return True
        
    except Exception as e:
        print(f"Error saving config template: {e}")
        return False


def load_config_template(config_path: str) -> Optional[Dict[str, Any]]:
    """
    Load a configuration template from file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration dictionary or None if failed
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config template: {e}")
        return None


def expand_environment_variables(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expand environment variables in configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configuration with expanded environment variables
    """
    import re
    
    def expand_value(value):
        if isinstance(value, str):
            # Replace ${VAR_NAME} with environment variable
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            for match in matches:
                env_value = os.getenv(match, f"${{{match}}}")  # Keep original if not found
                value = value.replace(f"${{{match}}}", env_value)
            return value
        elif isinstance(value, dict):
            return {k: expand_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [expand_value(item) for item in value]
        else:
            return value
    
    return expand_value(config)


def validate_config(config: Dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate a TARS configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required sections
    required_sections = ["memory_config", "llm_config", "knowledge_config"]
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: {section}")
    
    # Validate memory config
    if "memory_config" in config:
        memory_config = config["memory_config"]
        if "provider" not in memory_config:
            errors.append("Memory config missing 'provider'")
        elif memory_config["provider"] not in ["supabase", "qdrant", "chroma"]:
            errors.append(f"Invalid memory provider: {memory_config['provider']}")
    
    # Validate LLM config
    if "llm_config" in config:
        llm_config = config["llm_config"]
        if "model" not in llm_config:
            errors.append("LLM config missing 'model'")
    
    # Validate knowledge config
    if "knowledge_config" in config:
        knowledge_config = config["knowledge_config"]
        if "vector_store" not in knowledge_config:
            errors.append("Knowledge config missing 'vector_store'")
    
    return len(errors) == 0, errors


def generate_config_templates(output_dir: str = ".tars/configs") -> bool:
    """
    Generate all default configuration templates.
    
    Args:
        output_dir: Directory to save configuration templates
        
    Returns:
        True if successful, False otherwise
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate different configuration templates
        templates = [
            ("default", "default", "supabase", "openai", "qdrant", "default"),
            ("development", "development", "supabase", "openai", "qdrant", "default"),
            ("production", "production", "supabase", "openai", "qdrant", "comprehensive"),
            ("testing", "testing", "supabase", "openai", "qdrant", "default"),
            ("performance", "default", "supabase", "openai", "qdrant", "performance")
        ]
        
        for name, config_type, memory, llm, knowledge, workflow in templates:
            config = create_config_template(
                config_type=config_type,
                memory_provider=memory,
                llm_provider=llm,
                knowledge_provider=knowledge,
                workflow_profile=workflow
            )
            
            output_path = os.path.join(output_dir, f"{name}.json")
            if not save_config_template(config, output_path):
                return False
            
            print(f"✅ Generated config template: {output_path}")
        
        # Generate a README
        readme_content = """# TARS v1 Configuration Templates

This directory contains configuration templates for TARS v1.

## Available Templates

- **default.json**: Standard configuration with Supabase memory and OpenAI
- **development.json**: Development configuration with local Chroma database
- **production.json**: Production-optimized configuration
- **testing.json**: Testing configuration with local storage
- **performance.json**: High-performance configuration with Qdrant
- **local.json**: Fully local configuration (no cloud services)

## Usage

1. Copy a template: `cp default.json my-config.json`
2. Edit the configuration as needed
3. Set environment variables (see below)
4. Use with TARS: `python -m integrations.tars.v1.cli --config-file my-config.json`

## Environment Variables

Set these environment variables for cloud services:

```bash
# For OpenAI (if using OpenAI models)
export OPENAI_API_KEY="your-api-key"

# For Supabase (if using Supabase memory)
export SUPABASE_URL="your-supabase-url"
export SUPABASE_KEY="your-supabase-key"
```

## Customization

You can customize configurations by modifying:

- Memory provider (supabase, qdrant, chroma)
- LLM provider and model
- Knowledge base settings
- Workflow parameters
- Performance tuning options
"""
        
        readme_path = os.path.join(output_dir, "README.md")
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        print(f"✅ Generated README: {readme_path}")
        print(f"\n📁 All configuration templates saved to: {output_dir}")
        
        return True
        
    except Exception as e:
        print(f"Error generating config templates: {e}")
        return False


if __name__ == "__main__":
    # Generate all configuration templates
    success = generate_config_templates()
    if success:
        print("\n✅ All configuration templates generated successfully!")
    else:
        print("\n❌ Failed to generate configuration templates!")
