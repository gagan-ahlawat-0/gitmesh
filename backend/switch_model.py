#!/usr/bin/env python3
"""
GitMesh Model Configuration Switcher
===================================

Quick utility to switch between different LLM providers in GitMesh.
Usage: python switch_model.py [groq|gemini|openai]
"""

import os
import sys
from pathlib import Path

def update_env_file(provider: str, model: str, api_key_placeholder: str):
    """Update the .env file with new model configuration."""
    env_path = Path(__file__).parent / '.env'
    
    if not env_path.exists():
        print(f"❌ .env file not found at {env_path}")
        return False
    
    # Read current content
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Replace the model configuration lines
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        if line.startswith('MODEL_PROVIDER='):
            new_lines.append(f'MODEL_PROVIDER={provider}')
        elif line.startswith('MODEL_NAME='):
            new_lines.append(f'MODEL_NAME={model}')
        elif line.startswith('MODEL_KEY=') and not line.startswith('MODEL_KEY=your_'):
            # Keep existing API key if it's not a placeholder
            new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Write back to file
    with open(env_path, 'w') as f:
        f.write('\n'.join(new_lines))
    
    print(f"✅ Updated .env file:")
    print(f"   MODEL_PROVIDER={provider}")
    print(f"   MODEL_NAME={model}")
    print(f"   MODEL_KEY=<existing key kept>")
    
    return True

def main():
    if len(sys.argv) != 2:
        print("Usage: python switch_model.py [groq|gemini|openai]")
        print()
        print("Available configurations:")
        print("  groq   - Groq with Llama 3.1 70B")
        print("  gemini - Google Gemini 2.0 Flash")
        print("  openai - OpenAI GPT-4o Mini")
        return
    
    provider = sys.argv[1].lower()
    
    configurations = {
        'groq': {
            'model': 'llama-3.1-70b-versatile',
            'api_key_placeholder': 'your_groq_api_key'
        },
        'gemini': {
            'model': 'gemini-2.0-flash-exp',
            'api_key_placeholder': 'your_gemini_api_key'
        },
        'openai': {
            'model': 'gpt-4o-mini',
            'api_key_placeholder': 'your_openai_api_key'
        }
    }
    
    if provider not in configurations:
        print(f"❌ Unknown provider: {provider}")
        print(f"Available: {', '.join(configurations.keys())}")
        return
    
    config = configurations[provider]
    
    print(f"🔄 Switching to {provider.upper()} configuration...")
    
    if update_env_file(provider, config['model'], config['api_key_placeholder']):
        print()
        print(f"✅ Model configuration switched to {provider.upper()}!")
        print()
        print("Next steps:")
        print(f"1. Make sure your {provider.upper()} API key is set as MODEL_KEY in .env")
        print("2. Restart your application to load the new configuration")
        print()
        
        # Show current key status
        from dotenv import load_dotenv
        load_dotenv('.env')
        current_key = os.getenv('MODEL_KEY', '')
        if current_key and len(current_key) > 10:
            print(f"✅ MODEL_KEY is set ({len(current_key)} characters)")
        else:
            print(f"⚠️  MODEL_KEY needs to be set for {provider.upper()}")

if __name__ == '__main__':
    main()
