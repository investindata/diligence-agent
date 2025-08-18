# Input Sources System

This directory contains JSON files that define input sources for company analysis. Each file represents a company and contains structured information about various data sources used for due diligence.

## File Structure

Each JSON file follows this schema:

```json
{
  "company_name": "Company Name",
  "input_sources": [
    {
      "source": "Source Type",
      "identifier": "URL, channel, or identifier",
      "description": "Description of the information"
    }
  ]
}
```

## Supported Source Types

- **Google Docs**: Google Documents (requires "anyone with link" access)
- **Slack**: Slack channels or conversations
- **Webpage**: Web pages and websites
- **PDF**: PDF documents
- **Email**: Email communications
- **Database**: Database queries or exports
- **API**: API endpoints

## Example Files

- `baseten.json`: Input sources for Baseten due diligence
- `tensorstax.json`: Input sources for Tensorstax analysis

## Usage in Code

### Simple File-Based Configuration
To switch between companies, simply change the `COMPANY_FILE` variable in `src/diligence_agent/main.py`:

```python
# Change this line to switch companies
COMPANY_FILE = "baseten.json"  # Options: "baseten.json", "tensorstax.json"
```

### Running the Analysis
```bash
# Run with default company (baseten)
uv run diligence_agent

# Or run directly
uv run python -m diligence_agent.main
```

### Programmatic Usage
```python
from diligence_agent.input_reader import InputReader

# Create reader
reader = InputReader()

# Get formatted text for crew input
input_sources_text = reader.to_text("baseten.json")

# Use in crew
inputs = {
    'company_name': 'Baseten',
    'input_sources': input_sources_text
}
```

## Adding New Companies

1. Create a new JSON file: `company_name.json`
2. Follow the schema above
3. Add your input sources with proper descriptions
4. Ensure all URLs are accessible and properly formatted

## Validation

The system automatically validates:
- Required fields are present
- Source types are valid
- At least one input source is provided
- JSON syntax is valid
