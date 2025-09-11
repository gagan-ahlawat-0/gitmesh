# TARS v1 - Tactical AI Resource System

A comprehensive multi-agent system for open source project analysis, resource acquisition, and intelligent conversation management.

## Features

### 🤖 Multi-Agent Architecture
- **Resource Acquisition Layer**: 6 specialized agents for web crawling, code analysis, document processing, data analysis, GitHub integration, and knowledge management
- **Analysis/Intelligence Layer**: 4 specialized agents for technical analysis, competitive analysis, trend analysis, and project health assessment  
- **Conversation/Session Layer**: 1 orchestrator agent for managing interactions and coordinating workflows

### 🧠 Advanced AI Capabilities
- **Hybrid Memory System**: Short-term, long-term, and entity memory with RAG capabilities
- **Knowledge Base Integration**: Vector-based knowledge storage with semantic search
- **Intelligent Workflows**: Automated orchestration of acquisition, analysis, and conversation flows
- **Guardrails**: Built-in safety and quality controls for AI operations

### 🔧 Extensible Framework
- Built on the proven `ai` framework from GitMesh
- Modular design with clean separation of concerns
- Configurable memory, knowledge, and LLM providers
- Rich tool ecosystem for specialized tasks

## Quick Start

### Installation

1. Clone the repository and navigate to the TARS v1 directory:
```bash
cd integrations/tars/v1
```

2. Install dependencies (from the main project root):
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# For OpenAI (recommended)
export OPENAI_API_KEY="your-openai-api-key"

# For Supabase memory (optional, defaults to local storage)
export SUPABASE_URL="your-supabase-url"
export SUPABASE_KEY="your-supabase-key"
```

### Usage

#### Interactive Mode
```bash
python -m integrations.tars.v1.cli --interactive
```

#### Project Analysis
```bash
# Analyze a GitHub repository
python -m integrations.tars.v1.cli --analyze-project \
  --urls "https://github.com/owner/repo" \
  --repositories "https://github.com/owner/repo.git"

# Analyze multiple sources
python -m integrations.tars.v1.cli --analyze-project \
  --urls "https://project-website.com" \
  --repositories "https://github.com/owner/repo.git" \
  --documents "/path/to/docs.pdf" \
  --github-repos "owner/repo"
```

#### Single Query
```bash
python -m integrations.tars.v1.cli --query "What are the latest trends in AI/ML frameworks?"
```

#### System Status
```bash
python -m integrations.tars.v1.cli --status
```

### Python API

```python
from integrations.tars.v1 import TarsMain

# Initialize TARS
tars = TarsMain(user_id="developer", verbose=True)
await tars.initialize()

# Analyze a project
results = await tars.analyze_project(
    web_urls=["https://github.com/owner/repo"],
    repositories=["https://github.com/owner/repo.git"],
    github_repos=["owner/repo"]
)

# Interactive conversation
await tars.start_interactive_mode()

# Single query
response = await tars.process_query("Explain the architecture of this project")

# Cleanup
await tars.shutdown()
```

## Architecture

### Resource Acquisition Layer
- **WebCrawlerAgent**: Crawls and extracts content from web pages
- **CodeRepositoryAgent**: Analyzes Git repositories and code structure
- **DocumentAnalysisAgent**: Processes PDFs, Word docs, presentations
- **DataProcessingAgent**: Handles CSV, Excel, JSON data files  
- **GitHubIssueAgent**: Analyzes GitHub issues, PRs, and discussions
- **KnowledgeIntegrationAgent**: Manages knowledge base operations

### Analysis/Intelligence Layer
- **TechnicalAnalysisAgent**: Deep technical analysis of code and architecture
- **CompetitiveAnalysisAgent**: Competitive landscape and comparison analysis
- **TrendAnalysisAgent**: Technology trends and market analysis
- **ProjectHealthAgent**: Project health metrics and sustainability analysis

### Conversation/Session Layer
- **ConversationOrchestratorAgent**: Manages user interactions and workflow coordination

### Workflow System
- **AcquisitionWorkflow**: Orchestrates resource acquisition tasks
- **AnalysisWorkflow**: Coordinates analysis operations
- **ConversationWorkflow**: Manages interactive conversations

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
