#!/usr/bin/env python3
"""
Test script for the SentimentAnalyzer tool with Perplexity integration
"""

import sys
import os
from pathlib import Path

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from diligence_agent.tools.sentiment_analyzer import SentimentAnalyzer

def test_sentiment_analyzer():
    """Test the sentiment analyzer with a company"""
    
    # Create the tool instance
    analyzer = SentimentAnalyzer()
    
    # Parse command line arguments
    company_name = "OpenAI"  # Default
    company_domain = None
    company_description = None
    
    if len(sys.argv) > 1:
        company_name = sys.argv[1]
    if len(sys.argv) > 2:
        company_domain = sys.argv[2]
    if len(sys.argv) > 3:
        company_description = " ".join(sys.argv[3:])
    
    print(f"\n{'='*60}")
    print(f"Testing SentimentAnalyzer")
    print(f"{'='*60}")
    print(f"Company: {company_name}")
    if company_domain:
        print(f"Domain: {company_domain}")
    if company_description:
        print(f"Description: {company_description}")
    print(f"{'='*60}\n")
    
    # Check which API will be used
    if os.getenv('PERPLEXITY_API_KEY'):
        print("✅ Using Perplexity AI for enhanced sentiment analysis")
    else:
        print("ℹ️  Using SerperDev for sentiment analysis (Perplexity API key not found)")
    
    print("\nAnalyzing sentiment... (this may take 10-30 seconds)\n")
    
    try:
        # Run the sentiment analysis
        result = analyzer._run(company_name, company_domain, company_description)
        
        print(f"{'='*60}")
        print("RESULTS:")
        print(f"{'='*60}\n")
        print(result)
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("\nUsage: python test_sentiment.py <company_name> [domain] [description]")
        print("\nExamples:")
        print('  python test_sentiment.py Stripe stripe.com "payment processing platform"')
        print('  python test_sentiment.py Extend extend.com "virtual card platform for businesses"')
        print('  python test_sentiment.py Extend helloextend.com "product protection and warranty service"')
        print("\nUsing default: OpenAI\n")
    
    test_sentiment_analyzer()