# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DiligenceAgent is a multi-agent AI system powered by CrewAI that automates investment due diligence for startup companies. The system processes company questionnaires, Slack conversations, and web research to generate comprehensive investment reports with 10 structured outputs.

## Architecture

### Core Components

**Flow-Based Architecture (Primary)**:
- `src/diligence_agent/flow.py` - Main DiligenceFlow using CrewAI Flow framework
- `src/diligence_agent/research_flow.py` - ResearchFlow for web research tasks
- Sequential data processing with async execution support

**Crew-Based Architecture (Legacy)**:
- `src/diligence_agent/crew.py` - DiligenceAgent crew with parallel/sequential task execution
- `src/diligence_agent/main.py` - Entry point with CLI interface and company selection

### Agent System (5 specialized agents)

All agents are defined in `src/diligence_agent/config/agents.yaml`:
- **data_organizer**: Validates and structures raw data from multiple sources
- **section_writer**: Writes specific report sections (overview, product, market, etc.)
- **report_writer**: Compiles sections into cohesive investment report
- **investment_decision_maker**: Creates executive summary with GO/NO-GO recommendations
- **founder_assessor**: Conducts background checks and founder due diligence

### Task Pipeline (10 sequential tasks)

Tasks are configured in `src/diligence_agent/config/tasks.yaml`:
1. **data_organizer_task**: JSON validation of company data
2. **overview_section_writer_task**: Company overview and mission
3. **why_interesting_section_writer_task**: Investment thesis
4. **product_section_writer_task**: Product/service analysis
5. **market_section_writer_task**: Market size and dynamics
6. **competitive_landscape_section_writer_task**: Competitive analysis
7. **team_section_writer_task**: Team backgrounds
8. **founder_assessment_task**: Founder background verification and rating
9. **report_writer_task**: Compiled full report
10. **executive_summary_task**: Final investment recommendation

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

**Interactive Mode**:
```bash
crewai run
# or
python -m diligence_agent.main
```

**Command Line**:
```bash
crewai run tensorstax baseten          # Multiple companies
crewai run --all                       # All companies
crewai run --list                      # List available companies
```

**Flow-based execution**:
```bash
python src/diligence_agent/flow.py                    # Run full flow
python src/diligence_agent/flow.py FLOW_ID            # Resume specific flow
python src/diligence_agent/flow.py FLOW_ID "Final Report"  # Run specific section
python src/diligence_agent/flow.py FLOW_ID "Market" "Product"  # Run multiple sections
```

### Testing

```bash
pytest tests/                          # Run all tests
pytest tests/test_main.py              # Specific test file
python -m pytest -v                    # Verbose output
```

**Test Structure**:
- Integration tests in `tests/test_*.py`
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

Company data stored in `input_sources/`:
- JSON files with company information (e.g., `tensorstax.json`, `baseten.json`)
- Referenced by filename without extension in commands

### Output Structure

Generated in `output/session_TIMESTAMP/COMPANY_NAME/`:
- `1_data_validation.json` - Structured company data
- `2_overview_section.md` through `7_team_section.md` - Report sections
- `8_founder_assessment.md` - Founder due diligence
- `9_full_diligence_report.md` - Compiled report
- `10_executive_summary.md` - Final investment decision

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
- `src/diligence_agent/crew.py` - Agent and task definitions
- `src/diligence_agent/main.py` - CLI interface and company processing
- `src/diligence_agent/utils.py` - Common utilities and helper functions
- `src/diligence_agent/input_reader.py` - Company data input processing

## Recent Improvements

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