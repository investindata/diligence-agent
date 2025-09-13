# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DiligenceAgent is a flow-based AI system powered by CrewAI that automates investment due diligence for startup companies. The system processes Google Docs, websites, PDFs, and Slack conversations to generate comprehensive investment reports with structured outputs.

## Architecture

### Core Components

**Flow-Based Architecture**:
- `src/diligence_agent/flow.py` - Main DiligenceFlow using CrewAI Flow framework
- `src/diligence_agent/research_flow.py` - ResearchFlow for web research tasks  
- `src/diligence_agent/non_research_flow.py` - NonResearchFlow for analysis tasks
- Sequential data processing with async execution support
- LLM-based company name extraction from data sources documents

### Agent System (5 specialized agents)

All agents are defined in `src/diligence_agent/agents.py`:
- **organizer_agent**: Validates and structures raw data from multiple sources
- **search_agent**: Web research and data gathering
- **scraper_agent**: Website content extraction
- **writer_agent**: Writes specific report sections and compiles final reports
- **linkedin_agent**: Founder background checks and verification

### Flow Pipeline (10 sequential flow steps)

Flow steps are defined in `src/diligence_agent/flow.py`:
1. **Get Data Sources**: Extract company name and data sources from Google Doc
2. **Parse Data Sources**: Process Google Docs, websites, PDFs, Slack channels
3. **Company Overview**: Company background and mission analysis
4. **Product**: Product/service analysis with competitive research
5. **Competitive Landscape**: Market positioning and competitor analysis
6. **Market**: Market size, dynamics, and opportunity assessment
7. **Founders**: Team backgrounds and founder verification
8. **Why Interesting**: Investment thesis and rationale
9. **Report Conclusion**: Summary and investment recommendation
10. **Final Report**: Complete formatted investment report

### Key Data Structures

**Schemas** (`src/diligence_agent/schemas.py`):
- Company data validation models
- FounderNames for structured founder extraction
- Input/output data structures

**State Management**:
- `DiligenceState` in flow.py manages persistent state across tasks
- Supports skip_method for task resumption and parallel_execution toggle

## Development Commands

### Running Analysis

**Flow-based execution**:
```bash
# Run full flow with data sources URL
./diligence --sources "https://docs.google.com/document/d/DOCUMENT_ID/edit"

# Resume specific flow
./diligence --flow_id FLOW_ID

# Run specific sections only
./diligence --flow_id FLOW_ID --sections "Final Report,Market"

# Configure research parameters
./diligence --sources "URL" --search_terms 10 --websites 20

# Clear cache before running
./diligence --sources "URL" --clear_cache
```

**Direct Python execution**:
```bash
python src/diligence_agent/flow.py --sources "URL"           # Run full flow
python src/diligence_agent/flow.py --flow_id FLOW_ID         # Resume flow
python src/diligence_agent/flow.py --flow_id FLOW_ID --sections "Market,Product"  # Specific sections
```

### Testing

```bash
pytest tests/                          # Run all tests
pytest tests/test_flow_basic.py        # Flow-specific tests
python -m pytest -v                    # Verbose output
```

**Test Structure**:
- Integration tests in `tests/test_*.py`
- Flow tests in `tests/test_flow_basic.py`
- Fixtures in `tests/conftest.py`
- Sample data in `tests/fixtures/`

### UI Interface

```bash
python -m diligence_agent.ui           # Launch Gradio UI
# or use the 'ui' script defined in pyproject.toml
```

## Configuration and Setup

### Environment Variables

Required in `.env`:
- `OPENAI_API_KEY`: For LLM models (gpt-4o-mini, gpt-4.1, etc.)
- `SERPER_API_KEY`: For web search via SerperDevTool
- `SLACK_BOT_TOKEN`: For Slack integration (optional)
- Google OAuth credentials for Google Docs processing

### Input Data Structure

Data sources specified in Google Docs containing:
- **Company name**: Extracted via LLM from document content
- **Google docs**: List of Google Doc URLs
- **Websites**: List of website URLs to scrape
- **PDFs**: List of PDF file URLs or paths
- **Slack channels**: List of Slack channel IDs

### Output Structure

Generated in `task_outputs/COMPANY_NAME/`:
- `1.company_overview.md` - Company background analysis
- `2.product.md` - Product/service analysis
- `3.competitive_landscape.md` - Competition analysis
- `4.market.md` - Market analysis
- `5.founders.md` - Founder background verification
- `6.why_interesting.md` - Investment thesis
- `7.report_conclusion.md` - Investment recommendation
- `8.final_report.md` - Complete formatted report
- Google Doc automatically created in source document's Drive folder

## Tools and Integrations

### External Tools

- **SerperDevTool**: Web search for research tasks
- **SerperScrapeWebsiteTool**: Website content extraction
- **GoogleDocProcessor**: Google Docs/Sheets processing with automatic Google Drive integration
- **Slack Integration**: Channel data extraction via MCP tools
- **Google Drive Writer**: Automated creation of formatted Google Docs for final reports

### Model Configuration

- Default: `gpt-4o-mini` (cost-effective)
- Available: `gpt-4.1`, `gpt-4.1-mini`
- Temperature: 0.0-0.1 for consistent analysis
- Configurable via `--model` and `--temperature` flags

### Async Execution

- Flow-based architecture supports parallel task execution
- Toggle via `parallel_execution` parameter
- Sequential mode for debugging and cost management

## Key Files to Understand

- `src/diligence_agent/flow.py` - Main execution flow and state management
- `src/diligence_agent/research_flow.py` - Research tasks (overview, product, market, etc.)
- `src/diligence_agent/non_research_flow.py` - Analysis tasks (why interesting, conclusion)
- `src/diligence_agent/agents.py` - Agent definitions and configurations
- `src/diligence_agent/utils.py` - Utilities including Google Docs integration
- `src/diligence_agent/ui.py` - Gradio web interface
- `./diligence` - CLI script for running flows

## Recent Major Refactoring (2025-09-13)

### Deprecated Crew-Based Architecture
- Removed `crew.py`, `main.py`, `workflow.py` and related files
- Migrated fully to flow-based architecture
- Updated CLI interface to use `./diligence` script
- Simplified project structure and dependencies

### Google Docs Integration (2025-09-12)

**Final Report Google Docs Output**:
- Automatic creation of formatted Google Docs for final investment reports
- **File**: `utils.py:770` - `write_final_report_to_google_doc()` function
- **Document naming**: `{company_name}_Final_Report_{YYYY-MM-DD}_{H:MM:SS}pm` format
- **Folder placement**: Automatically placed in same Google Drive folder as source documents
- **Features**:
  - Full markdown to Google Docs formatting conversion
  - Bold text support in all elements (paragraphs, bullet points, numbered lists, headers)
  - Proper paragraph spacing (6pt after regular paragraphs)
  - Maintains document structure and formatting

**Markdown to Google Docs Conversion**:
- **File**: `utils.py:496-767` - `_convert_markdown_to_google_docs_format()` function
- **Supported formats**:
  - Headers (H1, H2, H3) → Google Docs heading styles
  - Bold text (`**text**`) → Bold formatting in all contexts
  - Bullet points (`- text`) → Google Docs bullet lists
  - Numbered lists (`1. text`) → Google Docs numbered lists
  - Regular paragraphs → Proper spacing and formatting

**Authentication**:
- Reuses existing Google OAuth credentials from GoogleDocProcessor
- Requires `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` environment variables

### Flow Execution Improvements

**Selective Section Execution**:
- **File**: `flow.py:285-347` - Enhanced `kickoff()` function
- **Usage**: `python src/diligence_agent/flow.py FLOW_ID "section1" "section2"`
- **Features**:
  - Resume existing flows with specific flow ID
  - Run only selected sections (e.g., "Final Report", "Market Analysis")
  - Skip completed sections automatically
  - Persistent state management across partial executions

**Full Context Integration**:
- All research methods now receive full context from previous sections
- Enhanced data flow between research and non-research flows
- Improved report coherence and completeness

### Output Organization

**Task Outputs Structure**:
- **Directory**: `task_outputs/{company_name}/`
- **Files**: Numbered sections (1.company_overview.md, 2.product.md, etc.)
- **Final report**: `8.final_report.md` with complete investment analysis
- **Google Docs**: Automatically created and linked in same Drive folder

## Development Notes

- Uses UV for dependency management (`uv.lock`)
- CrewAI framework for agent orchestration
- Opik integration for tracking (optional)
- Gradio UI for non-technical users
- Persistent state support for long-running analyses
- Google Drive integration for automated document creation and sharing