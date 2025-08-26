# Diligence Agent Documentation

## 📚 Documentation Index

### Getting Started
- [Quick Start Guide](../README.md) - Installation and basic usage
- [Business Guide](./BUSINESS_GUIDE.md) - Comprehensive business overview and use cases

### User Guides
- **[Command Line Interface](#command-line-interface)** - How to use the CLI
- **[Multi-Company Analysis](#multi-company-analysis)** - Analyzing multiple companies
- **[Data Validation](#data-validation)** - Understanding validation features

### Technical Documentation
- **[API Reference](#api-reference)** - Agent and task configurations
- **[Custom Agents](#custom-agents)** - Creating your own agents
- **[Integration Guide](#integration-guide)** - Integrating with other systems

---

## Command Line Interface

### Basic Usage
```bash
# Interactive mode - select companies from menu
./diligence

# Analyze specific company
./diligence tensorstax

# Analyze multiple companies
./diligence tensorstax baseten

# Analyze all available companies
./diligence --all

# List available companies
./diligence --list
```

### Output Structure
All outputs are saved to the `output/` directory:
```
output/
└── session_YYYYMMDD_HHMMSS/
    ├── tensorstax_executive_summary.md
    ├── baseten_executive_summary.md
    └── ALL_COMPANIES_SUMMARY.md
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

## API Reference

### Agent Configuration
Agents are configured in `src/diligence_agent/config/agents.yaml`:
- `data_organizer` - Validates and structures data
- `section_writer` - Writes report sections
- `report_writer` - Compiles final report
- `investment_decision_maker` - Makes investment recommendations

### Task Configuration
Tasks are dynamically generated based on company data.

## Custom Agents

To add a new agent:

1. Define agent in `config/agents.yaml`
2. Add agent method in `crew.py`
3. Create corresponding task
4. Update workflow as needed

## Integration Guide

### API Keys Required
- `OPENAI_API_KEY` - For GPT models
- `SERPER_API_KEY` - For web search validation

### Data Format
Companies are defined in JSON format:
```json
{
  "company_name": "Company Name",
  "company_sources": [...],
  "reference_sources": [...]
}
```

---

For more information, see the [Business Guide](./BUSINESS_GUIDE.md) or the main [README](../README.md).