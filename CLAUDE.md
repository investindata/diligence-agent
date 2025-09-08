# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Context

This is a CrewAI-based multi-agent system for investment due diligence analysis. When working with this codebase, prioritize:

1. **Code Quality**: Maintain clean, readable code following existing patterns
2. **Testing**: Always run tests after changes and add tests for new features  
3. **Agent Architecture**: Understand the 4-agent workflow: data_organizer → section_writer → report_writer → investment_decision_maker
4. **Data Validation**: Prioritize accuracy and fact-checking in all analysis

## Common Development Commands

### Quick Commands for Development
- `crewai run` - Interactive mode to select and analyze companies
- `ui` - Launch web interface at http://localhost:7861
- `pytest` - Run all tests
- `uv sync` - Install/update dependencies

### Full Command Reference
- `python -m diligence_agent --list` - List available companies
- `python -m diligence_agent tensorstax` - Analyze specific company
- `python -m diligence_agent --all` - Analyze all companies
- `pytest tests/test_input_reader.py` - Run specific test file
- `pytest -v` - Run tests with verbose output

## Code Style and Patterns

### File Organization
- `src/diligence_agent/main.py` - CLI entry point
- `src/diligence_agent/crew.py` - Agent and task definitions
- `src/diligence_agent/config/` - Agent and task YAML configurations
- `input_sources/` - Company data JSON files
- `output/` - Generated reports (timestamped sessions)

### Coding Standards
- Follow existing Python patterns and imports
- Use Pydantic for data validation
- Maintain agent role separation - don't mix agent responsibilities
- Always validate input data before processing
- Use descriptive variable names that match the business domain

### Agent Development
- Each agent has specific role: data organization, section writing, report compilation, investment decisions
- Agents are defined in `config/agents.yaml` with corresponding methods in `crew.py`
- Tasks are defined in `config/tasks.yaml` and dynamically generated
- Always use web search tools for validation and fact-checking

## Testing Approach

### Test Priority
1. **Input validation** - Ensure company data is properly structured
2. **Agent functionality** - Test each agent's core responsibilities
3. **Integration** - Test the full pipeline with sample data
4. **Output validation** - Verify report generation and format

### Test Commands
- `pytest` - Run full test suite before any commit
- `pytest -v` - Verbose output for debugging
- `pytest tests/test_input_reader.py` - Test input validation specifically

## What to Avoid

- **Don't mix agent responsibilities** - Keep data_organizer focused on validation, section_writer on content creation, etc.
- **Don't skip validation** - Always verify external claims through web search
- **Don't hardcode company names** - Use the input_sources JSON structure
- **Don't ignore test failures** - Fix tests before committing changes
- **Don't modify core CrewAI patterns** - Follow the established agent → task → crew workflow

## What to Prioritize

- **Data accuracy** - Investment decisions depend on validated information
- **User experience** - Both CLI and web interface should be intuitive
- **Comprehensive analysis** - Cover all aspects: market, product, team, competition
- **Clear reporting** - Executive summaries must provide actionable GO/NO-GO recommendations
- **Error handling** - Gracefully handle missing data, API failures, invalid inputs

## Environment Setup

Required environment variables in `.env`:
```
OPENAI_API_KEY=your-key-here
SERPER_API_KEY=your-key-here
```

Optional for Slack integration:
```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_TEAM_ID=T-your-team-id
SLACK_CHANNEL_IDS=comma,separated,channel,ids
```

## Development Workflows

### Making Changes to Agents
1. Update agent definition in `config/agents.yaml`
2. Modify corresponding method in `crew.py`
3. Update task in `config/tasks.yaml` if needed
4. Run tests: `pytest -v`
5. Test with sample company: `python -m diligence_agent tensorstax`

### Adding New Features
1. Follow existing code patterns and imports
2. Add tests for new functionality
3. Update documentation if user-facing changes
4. Ensure all agents maintain their role boundaries

### Debugging Issues
- Use `pytest -v` for detailed test output
- Check `output/session_*/` for generated reports
- Verify API keys are set correctly in `.env`
- Review agent interactions in crew execution logs

## Important File References

- **Agent configs**: `src/diligence_agent/config/agents.yaml`
- **Task configs**: `src/diligence_agent/config/tasks.yaml`  
- **Main crew logic**: `src/diligence_agent/crew.py`
- **CLI entry**: `src/diligence_agent/main.py`
- **Input validation**: `src/diligence_agent/input_reader.py`
- **MCP integrations**: `src/diligence_agent/mcp_config.py`