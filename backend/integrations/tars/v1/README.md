```markdown
# GitIngest Tool - GitMesh Integration

A clean and simple GitIngest integration tool that automatically integrates with GitMesh's authentication system.

## Features

- **Automatic Authentication**: Seamlessly integrates with GitMesh's `KeyManager` to use stored GitHub tokens
- **Token Override**: Support for overriding authentication tokens for specific operations
- **Submodule Support**: Option to include repository submodules in analysis
- **Clean API**: Simple and intuitive interface with convenience functions
- **Public/Private Repos**: Handles both public and private GitHub repositories

## Authentication Integration

The tool automatically integrates with GitMesh's authentication system:

1. **KeyManager Integration**: Uses `config.key_manager.KeyManager` to retrieve GitHub tokens stored by the main application
2. **Automatic Fallback**: Falls back to public repository access if no authentication is available
3. **Token Override**: Allows manual token specification for specific operations
4. **Environment Variables**: Supports `GITHUB_TOKEN` and `GITHUB_PAT` environment variables

## Usage Examples

### Basic Usage

```python
from gitingest_tool import GitIngestTool

# Automatically uses KeyManager for authentication
tool = GitIngestTool()
result = tool.analyze_repository("https://github.com/username/repo")

if result["success"]:
    print(f"Summary: {result['summary']}")
    print(f"Tree: {result['tree']}")
    print(f"Content: {result['content']}")
```

### Token Override

```python
# Override token for specific operation
result = tool.analyze_repository(
    "https://github.com/username/private-repo", 
    token="github_pat_...",
    include_submodules=True
)
```

### Convenience Functions

```python
from gitingest_tool import extract_details, analyze_repository

# Simple extraction with automatic auth
summary, tree, content = extract_details("https://github.com/username/repo")

# Full analysis with automatic auth
result = analyze_repository("https://github.com/username/repo", include_submodules=True)
```

### Individual Components

```python
tool = GitIngestTool()

# Get specific components
summary = tool.get_summary("https://github.com/username/repo")
tree = tool.get_tree("https://github.com/username/repo")
content = tool.get_content("https://github.com/username/repo")
```

## API Reference

### GitIngestTool Class

#### `__init__(github_token: Optional[str] = None)`
Initialize the tool with optional token override.

#### `analyze_repository(repo_url: str, include_submodules: bool = False, token: Optional[str] = None) -> Dict[str, Any]`
Analyze a repository and return structured results.

**Returns:**
```python
{
    "success": bool,
    "repo_url": str,
    "summary": str,
    "tree": str,
    "content": str,
    "error": Optional[str]
}
```

#### `get_summary(repo_url: str, **kwargs) -> Optional[str]`
Get repository summary only.

#### `get_tree(repo_url: str, **kwargs) -> Optional[str]`
Get repository tree structure only.

#### `get_content(repo_url: str, **kwargs) -> Optional[str]`
Get repository content only.

### Convenience Functions

#### `analyze_repository(repo_url: str, github_token: Optional[str] = None, include_submodules: bool = False) -> Dict[str, Any]`
Analyze a repository with automatic auth integration.

#### `extract_details(repo_url: str, github_token: Optional[str] = None) -> Tuple[str, str, str]`
Extract repository details and return as tuple `(summary, tree, content)`.

## Requirements

- `gitingest` library: `pip install gitingest`
- GitMesh's `config.key_manager.KeyManager` for authentication integration

## Integration Notes

1. **Automatic Token Retrieval**: The tool automatically retrieves GitHub tokens from GitMesh's KeyManager
2. **Environment Variables**: Supports standard GitHub token environment variables as fallback
3. **Error Handling**: Graceful handling of authentication failures and API errors
4. **Logging**: Integrated logging with clear authentication status indicators

## Examples

See `example_usage.py` for comprehensive examples of all features and integration patterns.
````

## Configuration

TARS v1 supports multiple configuration profiles:

### Generate Configuration Templates
```bash
python -m integrations.tars.v1.config
```

This creates configuration templates in `.tars/configs/`:
- `default.json`: Standard configuration  
- `development.json`: Development settings
- `production.json`: Production-optimized
- `testing.json`: Testing configuration
- `performance.json`: High-performance setup
- `local.json`: Fully local (no cloud services)

### Custom Configuration
```bash
python -m integrations.tars.v1.cli --config-file my-config.json --interactive
```

## Advanced Features

### Memory System
- **Hybrid Memory**: Combines short-term, long-term, and entity memory
- **RAG Integration**: Retrieval-augmented generation for enhanced responses
- **Quality Scoring**: Intelligent memory quality assessment
- **Multiple Providers**: Supabase, Qdrant, Chroma support

### Knowledge Base
- **Vector Storage**: Semantic search capabilities
- **Adaptive Chunking**: Intelligent document chunking strategies
- **Cross-referencing**: Knowledge item relationships
- **Version Control**: Knowledge versioning and updates

### Workflow Orchestration
- **Parallel Execution**: Concurrent agent operations
- **Error Handling**: Robust error recovery and retry logic
- **Progress Tracking**: Real-time workflow monitoring
- **Rate Limiting**: Respectful API usage

### Tools & Integrations
- **Web Scraping**: Advanced web content extraction
- **Code Analysis**: Static code analysis and metrics
- **Document Processing**: Multi-format document handling
- **Data Analysis**: Statistical and exploratory data analysis
- **GitHub Integration**: Issues, PRs, repository analysis
- **Knowledge Operations**: Semantic search and retrieval

## Examples

### Analyzing an Open Source Project
```python
from integrations.tars.v1 import TarsMain

async def analyze_fastapi():
    tars = TarsMain(project_id="fastapi_analysis")
    await tars.initialize()
    
    results = await tars.analyze_project(
        web_urls=["https://fastapi.tiangolo.com/"],
        repositories=["https://github.com/tiangolo/fastapi.git"],
        github_repos=["tiangolo/fastapi"]
    )
    
    print(f"Analysis completed: {results['status']}")
    await tars.shutdown()
```

### Custom Workflow
```python
from integrations.tars.v1 import TarsSession, AcquisitionWorkflow

async def custom_analysis():
    session = TarsSession()
    
    # Custom acquisition workflow
    acquisition = AcquisitionWorkflow(session)
    data = await acquisition.execute({
        "targets": ["https://example.com"],
        "depth": 2,
        "filters": ["technical", "documentation"]
    })
    
    # Process results
    for item in data["acquired_resources"]:
        print(f"Acquired: {item['title']} - {item['type']}")
```

## Development

### Project Structure
```
tars/v1/
├── __init__.py          # Package initialization and exports
├── main.py              # Main application class
├── cli.py               # Command-line interface
├── config.py            # Configuration management
├── agents.py            # All agent implementations
├── workflows.py         # Workflow orchestration
├── tools.py             # Specialized tool implementations
├── models.py            # Pydantic data models
├── session.py           # Session management
└── README.md            # This file
```

### Testing
```bash
# Run tests with the testing configuration
python -m integrations.tars.v1.cli --config-file .tars/configs/testing.json --status
```

### Contributing
1. Follow the existing code structure
2. Add comprehensive docstrings
3. Use type hints consistently
4. Test with multiple configurations
5. Update documentation

## License

This project inherits the license from the parent GitMesh project.

## Support

For questions, issues, or contributions:
1. Check the existing issues in the parent repository
2. Review the configuration templates and documentation
3. Test with the development configuration first
4. Provide detailed error logs and configuration when reporting issues

---

**TARS v1** - Making open source project analysis intelligent, comprehensive, and accessible.
