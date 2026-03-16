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

### Bash Script Migration Page

The **Bash Script Migration** page provides enterprise-grade conversion of provisioning Bash scripts — including scripts that escape from Salt, Puppet, or Chef — directly into Ansible playbooks or full roles ready for AAP.

#### Input Options

- **Paste Script tab**: Type or paste Bash script content directly into the editor
- **Upload File tab**: Upload `.sh`, `.bash`, or `.txt` script files

#### Actions Available

| Button | What it does |
|--------|--------------|
| Analyse Script | Parses the script and shows all detected patterns |
| Convert to Ansible | Generates a playbook YAML with quality score and AAP hints |
| Generate Ansible Role | Generates a complete 11-file role structure (tasks, handlers, defaults, meta, README) |

#### Analysis Output

When you click **Analyse Script**, the page shows:

- **Metric cards** — counts of packages, services, file writes, downloads, users/groups, and security risks
- **Package installs** — manager, packages, target Ansible module, confidence score
- **Service control** — systemctl/service operations with Ansible mapping
- **File writes** — heredoc and redirect operations mapped to `ansible.builtin.copy`
- **Downloads** — curl/wget operations mapped to `ansible.builtin.get_url`
- **Users & Groups** — `useradd`/`groupadd` operations mapped to `ansible.builtin.user`/`group`
- **File permissions** — `chmod`/`chown` operations with recursive support
- **Git operations** — `git clone`/`pull`/`checkout` mapped to `ansible.builtin.git`
- **Archives** — `tar -x`/`unzip` mapped to `ansible.builtin.unarchive`
- **sed operations** — `sed -i` with lineinfile/replace recommendation
- **Cron jobs** — `crontab` operations with Ansible cron guidance
- **Firewall rules** — `ufw`/`firewall-cmd`/`iptables` with collection hints
- **Hostname** — `hostnamectl set-hostname` mapped to `ansible.builtin.hostname`
- **Environment variables** — extracted shell variables; sensitive ones flagged
- **Sensitive data** (red alert) — detected passwords, API keys, and private key material with vault recommendation; values are always redacted
- **CM escape calls** (orange warning) — `salt-call`, `puppet apply`, `chef-client` calls embedded in the script, with native Ansible guidance
- **Shell fallbacks** — lines with no direct module mapping, with `ansible.builtin.shell` fallback note

#### Conversion & Role Output

When you click **Convert to Ansible** or **Generate Ansible Role**, the page additionally shows:

- **Quality score panel** — letter grade (A–F), structured coverage percentage, shell fallback count, and ranked improvement list
- **AAP hints panel** — recommended Execution Environment image, credential types, survey variables derived from `export VAR=val` statements, and actionable notes
- **Playbook YAML** or **Role files** — syntax-highlighted output with a **Download** button

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

## Puppet Migration

The **Puppet Migration** page provides a web-based interface for converting Puppet manifests (`.pp` files) and module directories to Ansible playbooks.

### Location

Navigate to: **Chef** tab → **Puppet Migration**

### Input Options

The page supports two input modes selectable via a dropdown:

- **Manifest File Path**: Enter the path to a single `.pp` manifest file
- **Module Directory Path**: Enter the path to a Puppet module root directory to convert all manifests in the module

### Actions Available

The page has two sub-sections: **Analyse Puppet Manifest** (for single `.pp` files) and **Analyse Puppet Module** (for full module directories). Each sub-section provides these buttons:

| Button | Action |
|--------|--------|
| **Analyse Manifest** / **Analyse Module** | Extract and display all resources, classes, variables, and unsupported constructs |
| **Convert to Ansible** | Generate an Ansible playbook from all parsed resources |
| **Convert with AI** | Use an LLM to handle Hiera lookups, exported resources, and other unsupported constructs |

A **Download Playbook** button appears in the conversion result panel once a playbook has been generated.

### Analysis Output

The parse output shows:

- **Resources**: Each resource type, title, attributes, and source line number
- **Classes**: Puppet class definitions with parameters
- **Variables**: Variable assignments found in the manifest
- **Unsupported constructs**: Hiera lookups, exported/virtual resources, `create_resources`, and other constructs that require manual review, each with a line number and guidance note

### Conversion Output

The playbook preview shows the generated Ansible YAML with:

- One task per Puppet resource, using the idiomatic `ansible.builtin` module
- `ansible.builtin.debug` placeholder tasks for unsupported constructs, with a `msg` explaining what manual work is needed
- Download button to save the playbook to disk

### AI-Assisted Conversion

For manifests with Hiera lookups or other unsupported constructs, expand the **AI Settings** panel to configure:

- **AI Provider**: `anthropic`, `openai`, `watson`, or `lightspeed`
- **API Key**: Your provider's API key
- **Model**: Model name (default: `claude-3-5-sonnet-20241022`)

The AI-assisted converter sends only the unsupported construct descriptions and manifest structure to the LLM — no file system paths or credential values are included in the prompt.

---

## PowerShell Migration

### Location

Navigate to: **Ansible** tab → **PowerShell Migration**

### Script Input and Conversion

The page uses a single script input area with controls beneath it for all operations.

- **Script input area**: Paste your PowerShell provisioning script directly into the text area
- **Parse Script button**: Extracts all provisioning actions and displays a structured summary with action types, confidence levels, source line numbers, and a metrics summary
- **Warnings panel**: Lists unrecognised commands that will fall back to `win_shell`

#### Conversion tools

The PowerShell migration UI uses a single script input area with a row of controls beneath it. Conversion actions share the same context as the analysis results; there are no separate workflow tabs.

- **Playbook name field**: Optional text field to set the Ansible play name (default: `powershell_migration`)
- **Hosts field**: Optional text field to set the inventory group or host pattern (default: `windows`)
- **Convert to playbook button**: Generates the Ansible playbook YAML and shows it in an on-page preview panel
- **Playbook preview**: Syntax-highlighted YAML output rendered below the editor
- **Statistics summary**: Task count breakdown (idiomatic modules vs. `win_shell` fallbacks) displayed alongside the preview

#### Enterprise artefacts (single-page workflow)

Enterprise artefact generation reuses the same script input and operates on the analysed script in place. Output is rendered inline in the browser for inspection, and each artefact panel provides dedicated download buttons (for example: inventory, group vars, requirements, job template, role files, and playbook outputs).

**Fidelity report**

- **Generate fidelity report button**: Calculates the fidelity score for the script
- **Score display**: Percentage of actions fully automatable
- **Review list**: Actions needing manual attention
- **Recommendations**: Actionable suggestions for improving automation coverage
- **Report output**: JSON-style text shown in a scrollable panel that you can copy into your own files

**Ansible role scaffold**

- **Role name field**: Optional text field to set the role directory name
- **Playbook name field**: Optional text field to set the top-level playbook base name
- **Hosts field**: Optional text field to set the inventory group pattern
- **Generate role button**: Produces a role-style task structure as text output within the UI

**Inventory**

- **Hosts field**: Enter comma-separated Windows host names or IPs
- **WinRM port field**: Set the WinRM listener port (default: 5986)
- **SSL toggle**: Switch between HTTPS (default) and HTTP transport
- **Generate button**: Produces the INI inventory displayed inline

**requirements.yml**

- **Generate button**: Produces `requirements.yml` tailored to the script, displayed inline

**AWX Job Template**

- **Job template name field**: Display name for the AWX job template
- **Generate button**: Produces the importable job template JSON displayed inline

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
│   ├── bash_migration.py       # Bash script to Ansible conversion
│   ├── puppet_migration.py     # Puppet manifest/module to Ansible conversion
│   ├── powershell_migration.py # PowerShell to Windows Ansible conversion
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

## Salt Migration Tab

The **Salt** tab provides a dedicated interface for SaltStack-to-Ansible migrations, complementing the 12 Salt MCP tools with interactive visualisation and guided workflows.

### Accessing the Salt Tab

The Salt tab appears in the main navigation alongside the Chef migration and Ansible upgrade tabs. Launch the UI and select **Salt** to access all Salt migration features.

### Sub-tabs

The Salt tab is divided into eight sub-tabs, each corresponding to a stage of the migration workflow:

#### Parse SLS

Interactive parser for Salt SLS state files.

- **File selection**: Browse or enter a path to any `.sls` state file
- **State tree view**: Expandable tree showing every state declaration, its module, function, and parameters
- **Pillar references**: List of all pillar keys referenced in the file with their default values
- **Grain references**: Grain keys used for conditional logic
- **Requisite graph**: Visual representation of `require`, `watch`, and `onchanges` dependencies between states
- **Export**: Download parsed results as JSON for further analysis

#### Convert to Ansible

Single-file SLS-to-playbook conversion with live preview.

- **Source file**: Select an SLS file to convert
- **Live preview**: Converted Ansible playbook YAML displayed alongside the original SLS for comparison
- **Handler extraction**: `watch` requisites highlighted and extracted to a handlers section
- **Variable mapping**: Pillar references shown with their Ansible equivalent variable names
- **Copy to clipboard**: One-click copy of the generated YAML
- **Download**: Save the converted playbook as a `.yml` file

#### Pillar Files

Pillar-to-variables conversion interface.

- **Pillar browser**: Navigate your pillar directory tree
- **Variable classification**: Automatic identification of sensitive values (passwords, keys, tokens)
- **Output format selector**: Choose between `yaml` (all vars together) or `vault` (split into plain + vault files)
- **Preview pane**: Side-by-side preview of the generated `group_vars` file and Vault file
- **Bulk export**: Convert an entire pillar directory in one operation

#### Directory Scan

Full Salt state tree scanner and structural overview.

- **Directory picker**: Enter or browse to your Salt states root directory
- **Tree view**: Collapsible directory tree showing all SLS files
- **Summary statistics**: Total state files, unique modules used, states per directory
- **Include graph**: Visual map of cross-directory include relationships
- **Export manifest**: Download the full directory inventory as JSON

#### Assessment

Complexity scoring and effort estimation for a Salt directory.

- **Directory input**: Point to any Salt state directory
- **Complexity dashboard**: Visual complexity score (Low / Medium / High / Very High) with contributing factor breakdown
- **Effort estimate**: Estimated person-days with confidence range
- **Per-directory breakdown**: Table showing complexity score and estimated effort for each state directory
- **Risk register**: Identified risk factors with suggested mitigations
- **Migration order**: Recommended sequence for converting state directories (simplest first)
- **Export report**: Download the assessment as Markdown or JSON

#### Migration Plan

Phased migration planning with timeline generation.

- **Directory input**: Salt states directory to plan for
- **Timeline input**: Available migration timeline in weeks
- **Target platform selector**: Choose from Ansible Automation Platform (AAP), AWX (open source), or Ansible Core
- **Generated plan**: Week-by-week phased plan displayed in a structured timeline view
- **Phase breakdown**: Objectives, activities, and deliverables for each phase
- **Resource estimate**: Person-days per phase
- **Export**: Download the plan as Markdown for inclusion in project documentation

#### Batch Convert

Full directory-to-roles conversion for large-scale migrations.

- **Source directory**: Salt states directory to convert
- **Output directory**: Target directory for the generated Ansible roles structure
- **Conversion options**:
  - Generate `site.yml` orchestration playbook
  - Include role `README.md` files
  - Preserve original SLS comments as task comments
- **Progress tracking**: Real-time progress bar and per-file status during conversion
- **Conversion summary**: Count of roles created, tasks generated, and items flagged for manual review
- **Review panel**: List of states that required manual attention with explanatory notes
- **Download archive**: Package the entire generated roles structure as a ZIP or TAR archive

#### Inventory

`top.sls`-to-Ansible-inventory conversion.

- **top.sls file**: Select or enter path to your `top.sls`
- **Targeting analysis**: Visual breakdown of all targeting expressions by environment
- **Inventory preview**: Generated Ansible INI inventory displayed with group structure
- **Group mapping**: Table showing each Salt target expression and its corresponding Ansible group
- **Matcher support**: Handles glob, grain, compound, pcre, and nodegroup matchers
- **Export**: Download the generated inventory as `hosts.ini`

---

## See Also

- **[MCP Tools Reference](mcp-tools.md)** - All available MCP tools
- **[CLI Usage Guide](cli-usage.md)** - Command-line interface
- **[Migration Guide](../migration-guide/overview.md)** - Complete Chef migration methodology
- **[Salt Migration Guide](../migration-guide/salt-migration.md)** - Complete Salt migration methodology
- **[Security Documentation](../security.md)** - Security features and best practices</content>
<parameter name="filePath">/workspaces/souschef/docs/user-guide/ui.md
