# DiligenceAgent Crew

Welcome to the DiligenceAgent Crew project, powered by [crewAI](https://crewai.com). This template is designed to help you set up a multi-agent AI system with ease, leveraging the powerful and flexible framework provided by crewAI. Our goal is to enable your agents to collaborate effectively on complex tasks, maximizing their collective intelligence and capabilities.

## Features

- **Comprehensive Due Diligence**: Analyzes startups across multiple dimensions including market, product, team, and competition
- **Customer Sentiment Analysis**: Uses Perplexity AI to analyze real customer reviews, social media sentiment, and employee feedback
- **Data Validation**: Actively verifies claims through web searches and identifies red flags
- **Founder Assessment**: Deep analysis of founder backgrounds and founder-market fit
- **Interactive Company Addition**: Add new companies via Google Docs, local files, or direct text input
- **Multi-Source Support**: Processes data from Google Docs, PDFs, and various text formats

## Installation

Ensure you have Python >=3.10 <3.14 installed on your system. This project uses [UV](https://docs.astral.sh/uv/) for dependency management and package handling, offering a seamless setup and execution experience.

First, if you haven't already, install uv:

```bash
pip install uv
```

Next, navigate to your project directory and install the dependencies:

(Optional) Lock the dependencies and install them by using the CLI command:
```bash
crewai install
```
### Customizing

**Add your API keys into the `.env` file:**

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Required for web search and validation
SERPER_API_KEY=your_serper_api_key_here

# Optional - for enhanced sentiment analysis
PERPLEXITY_API_KEY=your_perplexity_api_key_here

# Optional - for private Google Docs access
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

- Modify `src/diligence_agent/config/agents.yaml` to define your agents
- Modify `src/diligence_agent/config/tasks.yaml` to define your tasks
- Modify `src/diligence_agent/crew.py` to add your own logic, tools and specific args
- Modify `src/diligence_agent/main.py` to add custom inputs for your agents and tasks

## Running the Project

To kickstart your crew of AI agents and begin task execution, run this from the root folder of your project:

### Interactive Mode (Recommended)
```bash
$ ./diligence
# Or
$ crewai run
```

This will present an interactive menu where you can:
1. Select existing companies to analyze
2. Add a new company via Google Doc URL, file, or text
3. Analyze multiple companies at once

### Command Line Mode
```bash
# Analyze a specific company
$ python -m src.diligence_agent.main baseten

# Analyze multiple companies
$ python -m src.diligence_agent.main baseten tensorstax

# Add and analyze a new company from Google Doc
$ python -m src.diligence_agent.main --doc-url "https://docs.google.com/document/d/YOUR_DOC_ID"

# Add and analyze a new company from local file
$ python -m src.diligence_agent.main --doc-path "path/to/company_info.txt"
```

### Testing Sentiment Analysis
```bash
# Test sentiment analyzer for a specific company
$ python tests/test_sentiment.py "CompanyName" "domain.com" "company description"

# Example
$ python tests/test_sentiment.py Stripe stripe.com "payment processing platform"
```

## Output

The system generates comprehensive reports in the `output/session_TIMESTAMP/` directory:
- `1_data_validation.json` - Validated company data with completeness scores
- `2_overview_section.md` - Company overview
- `3_why_interesting.md` - Investment thesis
- `4_product_section.md` - Product analysis
- `5_market_section.md` - Market analysis
- `6_competitive_landscape.md` - Competition analysis
- `7_team_section.md` - Team assessment
- `8_founder_assessment.md` - Founder evaluation with A/B/C rating
- `9_customer_sentiment.md` - Customer sentiment analysis with real quotes
- `10_full_diligence_report.md` - Complete investment report
- `11_executive_summary.md` - Executive summary with GO/NO-GO recommendation

## Key Agents

The diligence-agent Crew is composed of multiple AI agents, each with unique roles:

1. **Data Validator**: Verifies company information and identifies red flags
2. **Section Writers**: Create detailed report sections (overview, product, market, competition, team)
3. **Founder Assessment Expert**: Evaluates founder quality and founder-market fit
4. **Sentiment Analyst**: Analyzes customer reviews, social media, and employee feedback using Perplexity AI
5. **Report Writer**: Compiles all sections into a comprehensive report
6. **Investment Decision Maker**: Provides final GO/NO-GO recommendation

## Customer Sentiment Analysis

The sentiment analysis feature uses Perplexity AI to gather real customer feedback from:
- Review platforms (G2, Capterra, Trustpilot, Google Reviews)
- Social media (Twitter/X, Reddit, LinkedIn)
- Employee reviews (Glassdoor, Indeed)
- Community forums (Hacker News, Product Hunt)

### Features:
- **Real Quotes**: Includes actual customer quotes with source attribution
- **Verification Levels**: Marks quotes as [VERIFIED], [UNVERIFIED], or [INDIRECT]
- **Company Disambiguation**: Correctly identifies companies even with common names
- **Transparency**: Reports data limitations and potential biases
- **Red Flag Detection**: Identifies suspicious review patterns

## Support

For support, questions, or feedback regarding the DiligenceAgent Crew or crewAI.
- Visit our [documentation](https://docs.crewai.com)
- Reach out to us through our [GitHub repository](https://github.com/joaomdmoura/crewai)
- [Join our Discord](https://discord.com/invite/X4JWnZnxPb)
- [Chat with our docs](https://chatg.pt/DWjSBZn)

Let's create wonders together with the power and simplicity of crewAI.
