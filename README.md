# IID Diligence Agent

A CrewAI-based multi-agent system for investment due diligence analysis. The system uses multiple AI agents that collaborate to analyze companies and generate comprehensive investment reports with GO/NO-GO recommendations.

## Features

- **Multi-Agent Analysis**: 4 specialized AI agents working collaboratively
- **Web Interface**: Professional UI with real-time progress tracking
- **Command Line Interface**: Interactive and batch processing modes
- **Slack Integration**: Optional integration for reading channels and posting updates
- **Comprehensive Reports**: Executive summaries with GO/NO-GO investment recommendations
- **Data Validation**: Enhanced validation with completeness scores and fact-checking
- **Multiple Company Support**: Analyze single or multiple companies in batch

## Quick Start

### Prerequisites

- Python >=3.10 <3.14
- OpenAI API key
- Serper API key (for web search validation)

### Installation

1. Install UV package manager (if not already installed):
   ```bash
   pip install uv
   ```

2. Install dependencies:
   ```bash
   crewai install
   # or
   uv sync
   ```

3. Set up environment variables in `.env`:
   ```
   OPENAI_API_KEY=your-openai-api-key-here
   SERPER_API_KEY=your-serper-api-key-here
   ```

### Running the Application

#### Web Interface (Recommended)

Launch the due diligence web interface:
```bash
ui
# or
python src/diligence_agent/ui.py
```

Access at: http://localhost:7861

**Web Interface Features:**
- Company selection from available data sources
- Real-time analysis progress tracking
- Dynamic report viewing with automatic type detection
- Professional InvestInData branding
- Clean markdown rendering with metadata

#### Command Line Interface

**Using the diligence script (recommended):**

Interactive mode (select companies from menu):
```bash
./diligence
```

List available companies:
```bash
./diligence list
```

Analyze specific company:
```bash
./diligence tensorstax
```

Analyze multiple companies:
```bash
./diligence tensorstax baseten
```

Analyze all companies:
```bash
./diligence all
```

**Alternative commands:**
```bash
crewai run                                    # Interactive mode
python -m diligence_agent --list              # List companies
python -m diligence_agent tensorstax          # Analyze specific company
python -m diligence_agent --all               # Analyze all companies
```

## Multi-Company Analysis

The system can analyze multiple companies in a single session:

1. **Interactive Selection**: Choose companies from a menu
2. **Command Line**: Specify multiple companies  
3. **Batch Processing**: Analyze all companies with `--all`

Each company gets:
- Individual executive summary
- GO/NO-GO investment recommendation
- Risk assessment and next steps

## Input Data Format

Place company data files in the `input_sources/` directory as JSON files:

```json
{
  "company_name": "Example Company",
  "company_sources": [
    "https://example.com/about",
    "https://example.com/product"
  ],
  "reference_sources": [
    "Reference materials for report formatting"
  ]
}
```

## Output Structure

All outputs are saved to timestamped session directories:
```
output/
└── session_YYYYMMDD_HHMMSS/
    ├── tensorstax_executive_summary.md
    ├── baseten_executive_summary.md
    └── ALL_COMPANIES_SUMMARY.md
```

- `{company}_executive_summary.md`: Individual company analysis
- `ALL_COMPANIES_SUMMARY.md`: Multi-company session summary

## Data Validation

The enhanced Data Validator agent actively verifies claims:

### What Gets Validated
- Company founding date and location
- Team backgrounds via LinkedIn
- Funding rounds via news sources
- Market size claims
- Revenue and growth figures
- Competitor information

### Validation Output
Each analysis includes:
- **Completeness Score** (0-100%)
- **Verified Facts** - Confirmed through independent sources
- **Unverified Claims** - Could not be validated
- **Red Flags** - Suspicious or contradictory information
- **Data Gaps** - Missing critical information

## Slack Integration (Optional)

For Slack channel reading and posting capabilities:

### 1. Install Slack MCP Server
```bash
npm install -g @modelcontextprotocol/server-slack
```

### 2. Configure Slack App
1. Create a Slack app at https://api.slack.com/apps
2. Add Bot Token Scopes: `channels:read`, `channels:history`, `chat:write`, `groups:read`, `groups:history`
3. Install the app to your workspace
4. Get the Bot User OAuth Token (starts with `xoxb-`)

### 3. Set Environment Variables
Add to your `.env` file:
```
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_TEAM_ID=T-your-team-id-here
SLACK_CHANNEL_IDS=C1234567890,C0987654321  # Optional: comma-separated channel IDs
```

### 4. Agents with Slack Access
Currently the `data_organizer` agent has Slack tools enabled for enhanced data gathering.

## Architecture

### AI Agents

1. **Data Organizer**: Validates and fact-checks company data with web research
2. **Section Writer**: Writes individual report sections (Overview, Product, Market, etc.)
3. **Report Writer**: Compiles sections into cohesive reports
4. **Investment Decision Maker**: Creates executive summaries with investment recommendations

### Tools & Integrations

- **Web Search**: SerperDevTool for fact-checking and research
- **Website Scraping**: SerperScrapeWebsiteTool for additional context
- **Google Docs**: Custom GoogleDocProcessor for processing Google Docs/Sheets
- **Slack MCP**: 8 tools for reading channels/threads and posting messages
- **Model Context Protocol (MCP)**: External service integrations

### Technology Stack

- **CrewAI**: Multi-agent orchestration framework
- **OpenAI**: GPT-4o-mini and GPT-4.1 models
- **UV**: Python dependency management
- **Pydantic**: Data validation
- **Gradio**: Web interface framework

## Testing

Run all tests:
```bash
pytest
```

Run specific test file:
```bash
pytest tests/test_input_reader.py
```

Run with verbose output:
```bash
pytest -v
```

## Configuration

### Agent Configuration
Agents are configured in `src/diligence_agent/config/agents.yaml`:
- `data_organizer` - Validates and structures data
- `section_writer` - Writes report sections
- `report_writer` - Compiles final report
- `investment_decision_maker` - Makes investment recommendations

### Task Configuration
Tasks are dynamically generated based on company data in `config/tasks.yaml`.

### Customization
- Modify `src/diligence_agent/config/agents.yaml` to define your agents
- Modify `src/diligence_agent/generate_tasks_yaml.py` to define your tasks
- Modify `src/diligence_agent/crew.py` to add your own logic, tools and specific args
- Modify `src/diligence_agent/main.py` to add custom inputs for your agents and tasks

### Custom Agents

To add a new agent:

1. Define agent in `config/agents.yaml`
2. Add agent method in `crew.py`
3. Create corresponding task
4. Update workflow as needed

## Documentation

- [Business Guide](docs/BUSINESS_GUIDE.md) - Comprehensive business overview and use cases

## Contributing

1. Follow the existing code style and patterns
2. Add tests for new features
3. Update documentation as needed
4. Ensure all tests pass before submitting PRs

## Support

For support regarding the IID Diligence Agent:
- Check the documentation in the `docs/` folder
- Review existing issues and feature requests
- Follow CrewAI best practices from [crewAI documentation](https://docs.crewai.com)
