#!/usr/bin/env python3
"""
Check current rate limit status and clear any issues
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

async def check_rate_limits():
    """Check rate limit status"""
    try:
        from utils.rate_limit_utils import get_rate_limit_status
        from utils.github_utils import GitHubAPIClient
        
        # Check our internal rate limiter
        github_token = os.getenv('GITHUB_TOKEN', 'default')
        rate_limit_key = f"github_api_{github_token}"
        
        internal_status = get_rate_limit_status(rate_limit_key)
        print("🔍 Internal Rate Limiter Status:")
        print(f"   - Requests made: {internal_status['requests_made']}")
        print(f"   - Requests remaining: {internal_status['requests_remaining']}")
        print(f"   - Is limited: {internal_status['is_limited']}")
        
        # Check GitHub API rate limits
        client = GitHubAPIClient()
        try:
            data, headers = await client._make_request('GET', '/rate_limit', token=github_token)
            core_limit = data['resources']['core']
            
            print("\n📊 GitHub API Rate Limits:")
            print(f"   - Limit: {core_limit['limit']}")
            print(f"   - Used: {core_limit['used']}")
            print(f"   - Remaining: {core_limit['remaining']}")
            print(f"   - Reset: {core_limit['reset']}")
            
            if core_limit['remaining'] < 100:
                print("⚠️  GitHub API rate limit is running low!")
            else:
                print("✅ GitHub API rate limit is healthy")
                
        except Exception as e:
            print(f"❌ Error checking GitHub API rate limits: {e}")
        
    except Exception as e:
        print(f"❌ Error checking rate limits: {e}")

if __name__ == "__main__":
    asyncio.run(check_rate_limits())