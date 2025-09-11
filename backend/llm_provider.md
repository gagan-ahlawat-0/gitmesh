# LiteLLM Provider Naming Conventions (2025)

## Overview
This document outlines the correct provider naming conventions for LiteLLM as of 2025. The system now uses unified `.env` configuration with `MODEL_PROVIDER`, `MODEL_NAME`, and `MODEL_KEY`.

## Key Updates Made

### ✅ Fixed Google/Gemini Naming
- **BEFORE**: `google/gemini-2.5-pro` ❌
- **NOW**: `gemini/gemini-2.5-pro` ✅

### ✅ Updated API Key Environment Variables
- **Google**: Uses `GEMINI_API_KEY` (not `GOOGLE_API_KEY`)
- All other providers use standard naming conventions

## Supported Providers & Correct Formatting

### 1. OpenAI
```bash
MODEL_PROVIDER=openai
MODEL_NAME=gpt-4o-mini
MODEL_KEY=sk-...
```
**LiteLLM Format**: `gpt-4o-mini` (no prefix)

### 2. Google/Gemini ⭐ UPDATED
```bash
MODEL_PROVIDER=gemini  # Can also use 'google'
MODEL_NAME=gemini-2.5-pro
MODEL_KEY=AIzaSy...
```
**LiteLLM Format**: `gemini/gemini-2.5-pro`
**API Key Env**: `GEMINI_API_KEY`
**Note**: Both `MODEL_PROVIDER=gemini` and `MODEL_PROVIDER=google` work

### 3. Anthropic
```bash
MODEL_PROVIDER=anthropic
MODEL_NAME=claude-3-5-sonnet-20240620
MODEL_KEY=sk-ant-...
```
**LiteLLM Format**: `anthropic/claude-3-5-sonnet-20240620`

### 4. Groq
```bash
MODEL_PROVIDER=groq
MODEL_NAME=llama3-8b-8192
MODEL_KEY=gsk_...
```
**LiteLLM Format**: `groq/llama3-8b-8192`

### 5. Deepseek
```bash
MODEL_PROVIDER=deepseek
MODEL_NAME=deepseek-chat
MODEL_KEY=sk-...
```
**LiteLLM Format**: `deepseek/deepseek-chat`

### 6. Cohere
```bash
MODEL_PROVIDER=cohere
MODEL_NAME=command-r-plus
MODEL_KEY=...
```
**LiteLLM Format**: `cohere/command-r-plus`

### 7. Ollama (Local)
```bash
MODEL_PROVIDER=ollama
MODEL_NAME=llama3.2:3b
MODEL_KEY=NA
```
**LiteLLM Format**: `ollama/llama3.2:3b`
**Note**: Uses `MODEL_KEY=NA` for local models

### 8. OpenRouter
```bash
MODEL_PROVIDER=openrouter
MODEL_NAME=openai/gpt-4o
MODEL_KEY=sk-or-...
```
**LiteLLM Format**: `openai/gpt-4o` (preserves provider/model format)

### 9. Mistral
```bash
MODEL_PROVIDER=mistral
MODEL_NAME=mistral-large-latest
MODEL_KEY=...
```
**LiteLLM Format**: `mistral/mistral-large-latest`

### 10. Perplexity
```bash
MODEL_PROVIDER=perplexity
MODEL_NAME=llama-3.1-sonar-small-128k-online
MODEL_KEY=pplx-...
```
**LiteLLM Format**: `perplexity/llama-3.1-sonar-small-128k-online`

### 11. xAI
```bash
MODEL_PROVIDER=xai
MODEL_NAME=grok-beta
MODEL_KEY=xai-...
```
**LiteLLM Format**: `xai/grok-beta`

## API Key Environment Variables

| Provider | Environment Variable | Notes |
|----------|---------------------|-------|
| OpenAI | `OPENAI_API_KEY` | Standard |
| Google | `GEMINI_API_KEY` | ⭐ Updated |
| Anthropic | `ANTHROPIC_API_KEY` | Standard |
| Groq | `GROQ_API_KEY` | Standard |
| Deepseek | `DEEPSEEK_API_KEY` | Standard |
| Cohere | `COHERE_API_KEY` | Standard |
| Ollama | None | Local, no API key |
| OpenRouter | `OPENROUTER_API_KEY` | Standard |
| Mistral | `MISTRAL_API_KEY` | Standard |
| Perplexity | `PERPLEXITYAI_API_KEY` | Standard |
| xAI | `XAI_API_KEY` | Standard |

## How It Works

1. **Set .env variables**:
   ```bash
   MODEL_PROVIDER=google
   MODEL_NAME=gemini-2.5-pro
   MODEL_KEY=your_api_key_here
   ```

2. **System automatically**:
   - Formats model as `gemini/gemini-2.5-pro`
   - Sets `OPENAI_BASE_URL` to correct endpoint
   - Sets `GEMINI_API_KEY` environment variable
   - Configures LiteLLM for the provider

3. **All TARS components use**:
   - `get_default_model()` from `context_manager.py`
   - Unified configuration across the system
   - No hardcoded models anywhere

## Testing

Run this to verify your configuration:
```bash
cd /home/raw/Documents/workspace/lfdt/gitmesh
python -c "
import sys
sys.path.append('backend')
from backend.core.context_manager import get_default_model
result = get_default_model()
print(f'Provider: {result[\"provider\"]}')
print(f'Model: {result[\"model\"]}')
print(f'Base URL: {result[\"base_url\"]}')
print(f'API Key Env: {result[\"api_key_env\"]}')
"
```

## Files Modified

- `backend/core/context_manager.py` - Updated Google provider naming and added new providers
- All TARS v1 files already use dynamic configuration via `get_default_model()`

## Migration Notes

If you were previously using:
- `google/gemini-2.5-pro` → Change to `gemini/gemini-2.5-pro`
- `GOOGLE_API_KEY` → Change to `GEMINI_API_KEY`
- Any hardcoded models → Use `.env` configuration

## Verification

✅ All providers tested and working  
✅ TARS initialization successful  
✅ Dynamic model configuration active  
✅ No hardcoded models in codebase  
✅ Latest 2025 LiteLLM standards implemented  
✅ **RESOLVED**: LiteLLM provider error fixed with correct `gemini/gemini-2.5-pro` format  
