# Visual Migration Planning Interface

SousChef provides a modern web-based interface for interactive Chef-to-Ansible migration planning and visualisation. The UI complements the MCP tools and CLI with visual workflows, real-time analysis, and interactive dependency mapping.

## Overview

The SousChef UI is a Streamlit-based web application that provides:

- **Interactive Cookbook Analysis**: Upload and analyse Chef cookbooks with real-time feedback
- **Dual Effort Estimation**: Compare manual migration effort with AI-assisted SousChef time savings
- **Dependency Visualisation**: Network graphs showing cookbook relationships and migration ordering
- **Archive Upload Support**: Secure handling of cookbook archives with built-in security measures
- **Migration Planning Wizards**: Step-by-step guidance through complex migrations
- **Progress Tracking**: Real-time status updates for all analysis operations
- **Validation Reports**: Comprehensive conversion quality assessments

## Launching the UI

### Development Mode

```bash
# Using Poetry
poetry run souschef ui

# Using pip
souschef ui

# Custom port
souschef ui --port 8080
```

### Docker Deployment

```bash
# Build the image
docker build -t souschef-ui .

# Run the container
docker run -p 8501:8501 souschef-ui

# Or use docker-compose
docker-compose up
```

### Docker Compose (Recommended)

```yaml
version: '3.8'
services:
  souschef-ui:
    build: .
    ports:
      - "8501:8501"
    restart: unless-stopped
```

## Features

### Unified Cookbook Migration Interface

The **Migrate Cookbook** page provides a comprehensive interface for end-to-end Chef-to-Ansible migrations with analysis, conversion, and deployment capabilities:

#### Analysis & Conversion
- **Archive Upload**: Secure handling of ZIP and TAR archives with size limits and security validation
- **Directory Scanning**: Interactive exploration of cookbook structures
- **Metadata Parsing**: Automatic extraction of cookbook dependencies, versions, and attributes
- **Dual Effort Estimation**:
  - **Manual Migration**: Estimated effort without AI assistance
  - **AI-Assisted with SousChef**: 50% time reduction through automated boilerplate conversion
  - **Time Savings**: Clearly displayed comparison showing hours and percentage saved
- **Complexity Assessment**: Real-time calculation of migration effort and risk factors
- **Holistic Analysis**: Analyse all cookbooks together considering inter-cookbook dependencies
- **Individual Selection**: Choose specific cookbooks for targeted analysis
- **Project Analysis**: Analyse selected cookbooks as a cohesive project with dependency tracking

#### Deployment & Orchestration
- **Platform Selection**: Target AWX (Open Source), Ansible Automation Platform, or Ansible Tower (Legacy)
- **Deployment Modes**:
  - **Simulation Mode**: Preview AWX/AAP deployment without creating actual resources
  - **Live Deployment**: Execute end-to-end migration with actual resource creation
- **Platform Connection**: Configure server URL, credentials, and SSL verification for live deployments
- **Conversion Options** (expandable):
  - Generate Git repository structure
  - Convert InSpec tests to Ansible tests
  - Convert Chef Habitat plans to Docker/Compose
  - Create TAR archives of converted files
  - Generate CI/CD pipeline configurations
  - Validate generated Ansible playbooks
- **Advanced Options**:
  - Specify Chef version being migrated from
  - Custom output directory for generated files
  - Preserve code comments during conversion

### Interactive Dependency Visualisation

Powered by NetworkX and Plotly for sophisticated dependency analysis:

- **Graph Analysis**: Automatic detection of cookbook dependencies and circular references
- **Interactive Exploration**: Zoom, pan, and hover over nodes to explore relationships
- **Color Coding**: Visual distinction between cookbooks, dependencies, and circular dependencies
- **Migration Ordering**: Automatic calculation of optimal migration sequences

### Real-Time Progress Tracking

All analysis operations include comprehensive progress feedback:

- **Progress Bars**: Visual indicators for long-running operations
- **Status Updates**: Real-time messages during analysis phases
- **Operation Tracking**: Separate progress tracking for dependency analysis and validation
- **Error Handling**: Graceful error display with recovery suggestions

### Migration Planning Wizards

Step-by-step guidance through complex migration scenarios:

- **Assessment Wizard**: Gather requirements and analyse migration scope
- **Planning Wizard**: Generate phased migration plans with timelines
- **Validation Wizard**: Test conversions and verify accuracy
- **Reporting Wizard**: Create executive and technical migration reports

### AI Settings and Configuration

Configure AI providers for enhanced analysis and repository selection:

- **Provider Selection**: Choose from Anthropic (Claude), OpenAI (GPT), IBM Watsonx, Red Hat Lightspeed, or Local Models
- **Local Model Support**: Connect to local model servers without requiring API keys
  - **Ollama**: Default local model server (http://localhost:11434)
  - **llama.cpp**: Lightweight local inference
  - **vLLM**: High-performance inference server
  - **LM Studio**: User-friendly local model interface
- **Configuration Validation**: Test connection to AI providers before saving
- **Model Selection**: Choose specific models based on your provider
- **Secure Storage**: API keys stored in user-specific configuration directory (~/.souschef/)

## Archive Upload Security

The UI includes comprehensive security measures for archive handling:

### Security Features

- **Size Limits**: Maximum archive size of 100MB, individual files limited to 50MB
- **File Count Limits**: Maximum 1,000 files per archive
- **Depth Limits**: Maximum directory depth of 10 levels
- **Path Traversal Protection**: Prevention of directory traversal attacks
- **Extension Blocking**: Rejection of executable files and dangerous extensions
- **Symlink Detection**: Identification and blocking of symbolic links
- **Archive Bomb Protection**: Detection of compressed archives designed to exhaust resources

### Supported Formats

- **ZIP Archives** (`.zip`)
- **TAR Archives** (`.tar`, `.tar.gz`, `.tar.bz2`, `.tar.xz`)
- **Automatic Detection**: Format detection based on file signatures, not extensions

### Error Handling

Clear, actionable error messages for security violations:

- **Size exceeded**: "Archive too large (150MB). Maximum allowed: 100MB"
- **Too many files**: "Archive contains 1,200 files. Maximum allowed: 1,000"
- **Dangerous file**: "Archive contains executable file 'malware.exe'. Upload rejected"
- **Path traversal**: "Archive contains path traversal attempt. Upload rejected"

## Usage Examples

### Analysing a Cookbook Archive

1. **Upload Archive**: Drag and drop or browse for a cookbook ZIP/TAR file
2. **Security Check**: UI validates archive security and displays results
3. **Analysis**: Automatic parsing of recipes, attributes, templates, and metadata
4. **Visualisation**: Interactive dependency graph showing relationships
5. **Reports**: Download analysis reports and migration recommendations

### Migration Planning

1. **Assessment**: Answer questions about migration scope and timeline
2. **Analysis**: UI analyses cookbooks and calculates complexity scores
3. **Planning**: Generate phased migration plans with task breakdowns
4. **Validation**: Test conversion accuracy and identify issues
5. **Reporting**: Create comprehensive migration documentation

## API Integration

The UI integrates with all SousChef MCP tools:

- **Real-time Tool Calls**: UI makes MCP tool calls for analysis operations
- **Progress Streaming**: Live updates from long-running tool executions
- **Error Propagation**: MCP tool errors displayed with user-friendly messages
- **Result Caching**: Intelligent caching of analysis results for performance

## Configuration

### Environment Variables

```bash
# UI Configuration
SOUSCHEF_UI_PORT=8501
SOUSCHEF_UI_HOST=0.0.0.0

# Security Settings
SOUSCHEF_MAX_ARCHIVE_SIZE=104857600  # 100MB in bytes
SOUSCHEF_MAX_FILE_SIZE=52428800      # 50MB in bytes
SOUSCHEF_MAX_FILES=1000
SOUSCHEF_MAX_DEPTH=10

# MCP Integration
SOUSCHEF_MCP_SERVER_URL=http://localhost:3000
```

### Docker Configuration

```yaml
version: '3.8'
services:
  souschef-ui:
    build: .
    ports:
      - "${SOUSCHEF_UI_PORT:-8501}:8501"
    environment:
      - SOUSCHEF_MAX_ARCHIVE_SIZE=104857600
      - SOUSCHEF_MAX_FILE_SIZE=52428800
    volumes:
      - ./uploads:/app/uploads
      - ./reports:/app/reports
```

## Troubleshooting

### Common Issues

**UI won't start**: Check that port 8501 is available and not blocked by firewall

**Archive upload fails**: Verify archive is under size limits and contains valid Chef cookbooks

**Analysis hangs**: Large cookbooks may take time; check progress indicators

**Dependency graph not showing**: Ensure NetworkX and Plotly are installed in the environment

### Performance Tuning

For large cookbook archives:

- Increase Docker memory limits: `docker run -m 2g souschef-ui`
- Use SSD storage for upload directories
- Configure larger timeouts for analysis operations
- Enable result caching for repeated analyses

### Security Considerations

- **Network Security**: Run UI behind reverse proxy with SSL termination
- **Access Control**: Implement authentication for production deployments
- **File Storage**: Use temporary storage with automatic cleanup
- **Rate Limiting**: Configure upload rate limits to prevent abuse

## Development

### Local Development Setup

```bash
# Install dependencies
poetry install

# Run with hot reload
poetry run streamlit run souschef/ui/app.py --server.headless true --server.port 8501

# Run tests
poetry run pytest tests/unit/test_ui.py
```

### UI Architecture

```
souschef/ui/
├── app.py              # Main Streamlit application
├── pages/              # Page modules
│   ├── cookbook_analysis.py    # Unified migration interface (analysis + orchestration)
│   ├── migration_planning.py   # Migration planning wizards
│   ├── ai_settings.py          # AI provider configuration
│   └── reports.py              # Report generation
├── components/         # Reusable UI components
│   ├── dependency_graph.py     # Network visualisation
│   ├── progress_tracker.py     # Progress indicators
│   └── security_validator.py   # Archive security checks
└── utils/              # Utility functions
    ├── archive_handler.py      # Secure archive processing
    ├── mcp_client.py          # MCP tool integration
    └── report_generator.py     # Report creation
```

## See Also

- **[MCP Tools Reference](mcp-tools.md)** - All available MCP tools
- **[CLI Usage Guide](cli-usage.md)** - Command-line interface
- **[Migration Guide](../migration-guide/overview.md)** - Complete migration methodology
- **[Security Documentation](../security.md)** - Security features and best practices</content>
<parameter name="filePath">/workspaces/souschef/docs/user-guide/ui.md
