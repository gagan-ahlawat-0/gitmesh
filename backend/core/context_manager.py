import os
from typing import List, Dict, Tuple
import structlog
from dotenv import load_dotenv

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, use system environment variables

logger = structlog.get_logger(__name__)

def _get_provider_config(provider: str) -> Tuple[str, str]:
    """
    Get base URL and API endpoint for a given provider.
    
    Returns:
        Tuple of (base_url, api_endpoint)
    """
    provider_configs = {
        'openai': ('https://api.openai.com/v1', ''),
        'google': (None, ''),  # Let LiteLLM handle Gemini URLs internally
        'anthropic': ('https://api.anthropic.com', ''),
        'groq': ('https://api.groq.com/openai/v1', ''),
        'ollama': ('http://localhost:11434/v1', ''),
        'openrouter': ('https://openrouter.ai/api/v1', ''),
        'deepseek': ('https://api.deepseek.com', ''),
        'cohere': ('https://api.cohere.ai/v1', ''),
        'mistral': ('https://api.mistral.ai/v1', ''),
        'vertex': ('https://us-central1-aiplatform.googleapis.com/v1', ''),
        'azure': ('https://api.cognitive.microsoft.com/sts/v1.0', ''),
        'perplexity': ('https://api.perplexity.ai', ''),
        'xai': ('https://api.x.ai/v1', ''),
    }
    
    return provider_configs.get(provider.lower(), ('https://api.openai.com/v1', ''))

def _detect_provider_and_configure(model_name: str) -> Tuple[str, str]:
    """
    Configure provider based on .env MODEL_PROVIDER or model name detection.
    
    Returns:
        Tuple of (formatted_model_name, base_url)
    """
    # First, check for explicit MODEL_PROVIDER in .env
    explicit_provider = os.getenv('MODEL_PROVIDER')
    
    if explicit_provider:
        provider = explicit_provider.lower()
        base_url, _ = _get_provider_config(provider)
        
        # Format model name with provider prefix for LiteLLM (except for OpenAI)
        if provider != 'openai' and '/' not in model_name:
            # Use correct LiteLLM format: 'google' for Google/Gemini models
            formatted_model = f"{provider}/{model_name}"
        else:
            formatted_model = model_name
            
        os.environ['OPENAI_BASE_URL'] = base_url
        logger.info(f"Using explicit provider '{provider}' from .env for model '{model_name}'")
        return formatted_model, base_url
    
    # Fallback: auto-detect provider from model name
    model_lower = model_name.lower()
    
    # Check for explicit provider prefixes in model name
    if '/' in model_name:
        provider, model = model_name.split('/', 1)
        base_url, _ = _get_provider_config(provider)
        os.environ['OPENAI_BASE_URL'] = base_url
        return model_name, base_url
    
    # Auto-detect provider from model name patterns
    if any(pattern in model_lower for pattern in ['gpt-', 'o1-', 'chatgpt']):
        base_url, _ = _get_provider_config('openai')
        formatted_model = model_name
    elif any(pattern in model_lower for pattern in ['gemini', 'palm-', 'bison', 'gecko']):
        base_url, _ = _get_provider_config('google')
        formatted_model = f"google/{model_name}"
    elif any(pattern in model_lower for pattern in ['claude', 'anthropic']):
        base_url, _ = _get_provider_config('anthropic')
        formatted_model = f"anthropic/{model_name}"
    elif any(pattern in model_lower for pattern in ['llama', 'mistral', 'qwen', 'codellama']):
        # Check if Ollama is explicitly configured
        existing_base_url = os.getenv('OPENAI_BASE_URL', '')
        if 'ollama' in existing_base_url.lower() or ':11434' in existing_base_url:
            base_url = existing_base_url
            formatted_model = f"ollama/{model_name}"
        else:
            # Default to Groq for these models
            base_url, _ = _get_provider_config('groq')
            formatted_model = f"groq/{model_name}"
    elif any(pattern in model_lower for pattern in ['deepseek']):
        base_url, _ = _get_provider_config('deepseek')
        formatted_model = f"deepseek/{model_name}"
    elif any(pattern in model_lower for pattern in ['command-', 'cohere']):
        base_url, _ = _get_provider_config('cohere')
        formatted_model = f"cohere/{model_name}"
    else:
        # Default to OpenAI
        base_url, _ = _get_provider_config('openai')
        formatted_model = model_name
        logger.warning(f"Unknown model provider for {model_name}, defaulting to OpenAI")
    
    if base_url:
        os.environ['OPENAI_BASE_URL'] = base_url
    return formatted_model, base_url

def get_default_model() -> Dict[str, str]:
    """
    Get the default model from environment configuration using MODEL_PROVIDER, MODEL_NAME, and MODEL_KEY.
    
    This function uses the explicit provider configuration from .env and sets up the appropriate
    base URL and API key environment variables for LiteLLM.
    
    Returns:
        Dict containing 'model', 'provider', 'base_url', and 'api_key_env' keys
    """
    # Load .env file first
    load_dotenv()
    
    model_provider = os.getenv('MODEL_PROVIDER', '').lower()
    model_name = os.getenv('MODEL_NAME', '')
    model_key = os.getenv('MODEL_KEY', '')
    
    if not model_provider or not model_name:
        logger.warning("MODEL_PROVIDER or MODEL_NAME not configured, using fallback")
        return {
            'model': 'gpt-4o-mini',
            'provider': 'openai',
            'base_url': 'https://api.openai.com/v1',
            'api_key_env': 'OPENAI_API_KEY'
        }
    
    # Provider-specific configuration (latest 2025 standards)
    provider_configs = {
        'openai': {
            'base_url': 'https://api.openai.com/v1',
            'format': lambda name: name,  # OpenAI models use direct names
            'api_key_env': 'OPENAI_API_KEY'
        },
        'google': {
            'base_url': None,  # Let LiteLLM handle Gemini URLs internally
            'format': lambda name: f"gemini/{name}" if not name.startswith('gemini/') else name,
            'api_key_env': 'GEMINI_API_KEY'
        },
        'gemini': {  # Alias for google - more intuitive naming
            'base_url': None,  # Let LiteLLM handle Gemini URLs internally
            'format': lambda name: f"gemini/{name}" if not name.startswith('gemini/') else name,
            'api_key_env': 'GEMINI_API_KEY'
        },
        'anthropic': {
            'base_url': 'https://api.anthropic.com',
            'format': lambda name: f"anthropic/{name}" if not name.startswith('anthropic/') else name,
            'api_key_env': 'ANTHROPIC_API_KEY'
        },
        'groq': {
            'base_url': 'https://api.groq.com/openai/v1',
            'format': lambda name: f"groq/{name}" if not name.startswith('groq/') else name,
            'api_key_env': 'GROQ_API_KEY'
        },
        'ollama': {
            'base_url': 'http://localhost:11434/v1',
            'format': lambda name: f"ollama/{name}" if not name.startswith('ollama/') else name,
            'api_key_env': None  # Ollama doesn't need API key
        },
        'openrouter': {
            'base_url': 'https://openrouter.ai/api/v1',
            'format': lambda name: name if '/' in name else f"openrouter/{name}",  # OpenRouter supports direct provider/model format
            'api_key_env': 'OPENROUTER_API_KEY'
        },
        'deepseek': {
            'base_url': 'https://api.deepseek.com',
            'format': lambda name: f"deepseek/{name}" if not name.startswith('deepseek/') else name,
            'api_key_env': 'DEEPSEEK_API_KEY'
        },
        'cohere': {
            'base_url': 'https://api.cohere.ai/v1',
            'format': lambda name: f"cohere/{name}" if not name.startswith('cohere/') else name,
            'api_key_env': 'COHERE_API_KEY'
        },
        'vertex': {
            'base_url': 'https://us-central1-aiplatform.googleapis.com/v1',
            'format': lambda name: f"vertex_ai/{name}" if not name.startswith('vertex_ai/') else name,
            'api_key_env': 'GOOGLE_APPLICATION_CREDENTIALS'  # Service account JSON path
        },
        'azure': {
            'base_url': None,  # Set dynamically via AZURE_API_BASE
            'format': lambda name: f"azure/{name}" if not name.startswith('azure/') else name,
            'api_key_env': 'AZURE_API_KEY'
        },
        'mistral': {
            'base_url': 'https://api.mistral.ai/v1',
            'format': lambda name: f"mistral/{name}" if not name.startswith('mistral/') else name,
            'api_key_env': 'MISTRAL_API_KEY'
        },
        'perplexity': {
            'base_url': 'https://api.perplexity.ai',
            'format': lambda name: f"perplexity/{name}" if not name.startswith('perplexity/') else name,
            'api_key_env': 'PERPLEXITYAI_API_KEY'
        },
        'xai': {
            'base_url': 'https://api.x.ai/v1',
            'format': lambda name: f"xai/{name}" if not name.startswith('xai/') else name,
            'api_key_env': 'XAI_API_KEY'
        }
    }
    
    if model_provider not in provider_configs:
        logger.error(f"Unsupported MODEL_PROVIDER: {model_provider}")
        logger.info(f"Supported providers: {', '.join(provider_configs.keys())}")
        raise ValueError(f"Unsupported MODEL_PROVIDER: {model_provider}")
    
    config = provider_configs[model_provider]
    formatted_model = config['format'](model_name)
    base_url = config['base_url']
    api_key_env = config['api_key_env']
    
    # Set environment variables for LiteLLM compatibility
    if base_url:
        os.environ['OPENAI_BASE_URL'] = base_url
    
    # Set the appropriate API key environment variable
    if api_key_env and model_key and model_key.upper() != 'NA':
        os.environ[api_key_env] = model_key
        logger.info(f"Set {api_key_env} environment variable")
    elif api_key_env and (not model_key or model_key.upper() == 'NA'):
        if model_provider != 'ollama':
            logger.warning(f"MODEL_KEY not provided or set to 'NA' but required for {model_provider}")
    elif model_provider == 'ollama':
        logger.info("Ollama provider - no API key required")
    
    logger.info(f"Configured {model_provider} provider: {formatted_model} -> {base_url}")
    
    return {
        'model': formatted_model,
        'provider': model_provider,
        'base_url': base_url,
        'api_key_env': api_key_env
    }

class ContextWindow:
    def __init__(self, max_tokens: int = 4096, model: str = None):
        self.max_tokens = max_tokens
        self.model = model or get_default_model()
        try:
            import litellm
            self.token_counter = lambda text: litellm.token_counter(model=self.model, text=text)
        except ImportError:
            self.token_counter = lambda text: len(text.split()) * 1.3

    def count_tokens(self, messages: List[Dict]) -> int:
        text = " ".join([m.get("content", "") for m in messages])
        return int(self.token_counter(text))

    def truncate(self, messages: List[Dict]) -> List[Dict]:
        # Truncate messages to fit within max_tokens
        total_tokens = 0
        truncated = []
        for m in reversed(messages):
            tokens = int(self.token_counter(m.get("content", "")))
            if total_tokens + tokens > self.max_tokens:
                break
            truncated.insert(0, m)
            total_tokens += tokens
        if total_tokens > self.max_tokens:
            logger.warning("ContextWindow: Truncated messages to fit token limit.")
        return truncated 