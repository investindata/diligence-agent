from crewai.tools import BaseTool
from typing import Type, Optional, Dict, List
from pydantic import BaseModel, Field
from crewai_tools import SerperDevTool, SerperScrapeWebsiteTool
import re
from datetime import datetime
import json
import os
from openai import OpenAI


class SentimentAnalyzerInput(BaseModel):
    """Input schema for SentimentAnalyzer."""
    company_name: str = Field(..., description="The name of the company to analyze sentiment for")
    company_domain: Optional[str] = Field(None, description="Optional company domain/website to help identify the correct company (e.g., 'extend.com', 'stripe.com')")
    company_description: Optional[str] = Field(None, description="Optional brief description to help identify the company (e.g., 'corporate card platform', 'payment processor')")


class SentimentAnalyzer(BaseTool):
    name: str = "Sentiment Analyzer"
    description: str = (
        "Analyze customer sentiment and social media presence for a company using web search. "
        "Searches for actual mentions, reviews, and discussions across multiple platforms "
        "to gauge public perception and customer satisfaction."
    )
    args_schema: Type[BaseModel] = SentimentAnalyzerInput

    def _run(self, company_name: str, company_domain: Optional[str] = None, company_description: Optional[str] = None) -> str:
        """
        Analyze sentiment for a company using Perplexity AI for comprehensive social media analysis.
        """
        # Check if Perplexity API key is available
        perplexity_api_key = os.getenv('PERPLEXITY_API_KEY')
        
        if perplexity_api_key:
            # Use Perplexity for comprehensive sentiment analysis
            return self._analyze_with_perplexity(company_name, perplexity_api_key, company_domain, company_description)
        else:
            # Fall back to SerperDev tools
            return self._analyze_with_serper(company_name)
    
    def _analyze_with_perplexity(self, company_name: str, api_key: str, company_domain: Optional[str] = None, company_description: Optional[str] = None) -> str:
        """
        Use Perplexity AI to analyze sentiment and social media presence.
        """
        try:
            # Initialize Perplexity client (OpenAI-compatible)
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.perplexity.ai"
            )
            
            # Build company identifier string
            company_identifier = company_name
            if company_domain:
                company_identifier += f" ({company_domain})"
            if company_description:
                company_identifier += f" - {company_description}"
            
            # Create a comprehensive query for sentiment analysis
            query = f"""
            Please provide a comprehensive sentiment analysis for {company_identifier}.
            
            IMPORTANT: Make sure you're analyzing the correct company:
            - Company name: {company_name}
            {f'- Company website/domain: {company_domain}' if company_domain else ''}
            {f'- Company description: {company_description}' if company_description else ''}
            
            Please include:
            
            1. Customer Reviews & Ratings:
               - Search for reviews on platforms like Google Reviews, Trustpilot, G2, Capterra
               - Include average ratings and common complaints/praises
               - PROVIDE DIRECT QUOTES from actual reviews
               - Include URLs/links to the review pages when available
            
            2. Social Media Sentiment:
               - Twitter/X mentions and sentiment
               - Reddit discussions (especially r/technology, relevant industry subreddits)
               - LinkedIn presence and professional reputation
               - Facebook and Instagram mentions
               - INCLUDE SPECIFIC POST QUOTES and links to threads/posts where possible
            
            3. News & Media Coverage:
               - Recent news articles and their tone
               - Press coverage sentiment (positive/negative/neutral)
               - PROVIDE ARTICLE TITLES, QUOTES, and URLs
            
            4. Employee Sentiment:
               - Glassdoor reviews and ratings
               - Indeed reviews
               - Overall employee satisfaction
               - INCLUDE SPECIFIC REVIEW QUOTES and ratings
            
            5. Community & Forum Discussions:
               - Hacker News mentions (include thread URLs)
               - Product Hunt feedback (include specific comments)
               - Industry-specific forums
               - PROVIDE DIRECT QUOTES from discussions
            
            CRITICAL REQUIREMENTS FOR ACCURACY AND VERIFICATION:
            
            1. QUOTE AUTHENTICITY:
            - ONLY include quotes that you have directly found in your search results
            - DO NOT paraphrase or reconstruct quotes from memory
            - DO NOT create example quotes or hypothetical statements
            - If you cannot find exact quotes, explicitly state "No direct quotes found"
            
            2. SOURCE VERIFICATION:
            - ONLY provide URLs that you have actually accessed or verified exist
            - DO NOT construct or guess URLs based on patterns
            - Mark each source with confidence level:
              * [VERIFIED] - You found this exact quote at this source
              * [UNVERIFIED] - Information from search but cannot confirm exact source
              * [INDIRECT] - Information referenced but not directly accessed
            
            3. COMPANY DISAMBIGUATION:
            - ALWAYS verify you're analyzing the correct company
            - If multiple companies share the same name, explicitly note this
            - Cross-reference with the domain ({company_domain}) to ensure accuracy
            - Flag any reviews/quotes that might be about a different company
            
            4. TRANSPARENCY REQUIREMENTS:
            - If sentiment data is limited, state: "Limited public sentiment data available"
            - If no reviews found on a platform, state: "No reviews found on [Platform]"
            - If quotes are from company testimonials rather than independent reviews, note this
            - Distinguish between:
              * Independent customer reviews (most valuable)
              * Company-provided testimonials (potentially biased)
              * Employee reviews (different perspective)
              * Partner/investor statements (potentially biased)
            
            5. FORMAT FOR QUOTES:
            "Exact quote text" - [VERIFIED/UNVERIFIED] Source (Platform, Date) [URL if available]
            
            6. MINIMUM EVIDENCE THRESHOLD:
            - Include 5-10 quotes IF available
            - If fewer than 5 quotes found, explicitly state the limited data
            - Better to have 3 verified quotes than 10 uncertain ones
            
            7. RED FLAGS TO REPORT:
            - Very few or no independent reviews despite company age
            - All reviews from same time period (potential review bombing)
            - Inconsistent information across sources
            - Reviews that seem to be about a different company with same name
            """
            
            # Make the API call to Perplexity
            response = client.chat.completions.create(
                model="sonar-pro",  # Using the most advanced model for comprehensive search
                messages=[
                    {
                        "role": "system",
                        "content": """You are a sentiment analysis expert with strict accuracy requirements. 
                        
CRITICAL RULES:
1. NEVER fabricate or hallucinate quotes - only use exact quotes you find
2. NEVER guess or construct URLs - only provide URLs you've actually accessed
3. ALWAYS mark confidence levels: [VERIFIED], [UNVERIFIED], or [INDIRECT]
4. If you find limited data, say so explicitly rather than making up content
5. If reviews might be about a different company with the same name, flag this
6. Distinguish between independent reviews and company-provided testimonials

Your credibility depends on accuracy. It's better to report "no data found" than to provide false information."""
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                temperature=0.1,  # Lower temperature for more factual responses
                max_tokens=2000
            )
            
            # Extract the response
            analysis = response.choices[0].message.content
            
            # Format the results
            results = {
                "company": company_name,
                "analysis_date": datetime.now().isoformat(),
                "source": "Perplexity AI (Sonar Pro)",
                "comprehensive_analysis": analysis,
                "methodology": "AI-powered comprehensive web search and analysis across multiple platforms"
            }
            
            return json.dumps(results, indent=2)
            
        except Exception as e:
            print(f"Error using Perplexity API: {e}")
            print("Falling back to SerperDev tools...")
            return self._analyze_with_serper(company_name)
    
    def _analyze_with_serper(self, company_name: str) -> str:
        """
        Original implementation using SerperDev tools as fallback.
        """
        # Initialize tools inside _run method
        search_tool = SerperDevTool()
        scrape_tool = SerperScrapeWebsiteTool()
        results = {
            "company": company_name,
            "analysis_date": datetime.now().isoformat(),
            "source": "SerperDev Web Search",
            "platforms_searched": [],
            "findings": [],
            "overall_assessment": "",
            "limitations": []
        }
        
        # Define search queries for different aspects
        search_queries = [
            {
                "query": f'"{company_name}" reviews customers rating',
                "type": "customer_reviews",
                "platforms": ["Google Reviews", "Trustpilot", "G2", "Capterra"]
            },
            {
                "query": f'"{company_name}" site:reddit.com',
                "type": "reddit_discussions",
                "platforms": ["Reddit"]
            },
            {
                "query": f'"{company_name}" site:twitter.com OR site:x.com',
                "type": "twitter_mentions",
                "platforms": ["Twitter/X"]
            },
            {
                "query": f'"{company_name}" glassdoor reviews employees',
                "type": "employee_sentiment",
                "platforms": ["Glassdoor"]
            },
            {
                "query": f'"{company_name}" complaints problems issues',
                "type": "negative_sentiment",
                "platforms": ["Various"]
            },
            {
                "query": f'"{company_name}" "love" OR "excellent" OR "amazing" customer',
                "type": "positive_sentiment",
                "platforms": ["Various"]
            }
        ]
        
        # Perform actual searches
        for search_config in search_queries:
            try:
                # Use the search tool to find real information
                search_results = search_tool._run(search_config["query"])
                
                # Parse and analyze the results
                finding = {
                    "search_type": search_config["type"],
                    "platforms": search_config["platforms"],
                    "query": search_config["query"],
                    "raw_results": search_results[:500],  # Limit for readability
                    "summary": self._extract_sentiment_from_results(search_results, search_config["type"])
                }
                
                results["findings"].append(finding)
                results["platforms_searched"].extend(search_config["platforms"])
                
            except Exception as e:
                results["limitations"].append(f"Could not search {search_config['type']}: {str(e)}")
        
        # Generate overall assessment based on real findings
        results["overall_assessment"] = self._generate_overall_assessment(results["findings"])
        
        # Remove duplicates from platforms_searched
        results["platforms_searched"] = list(set(results["platforms_searched"]))
        
        return self._format_results(results)
    
    def _extract_sentiment_from_results(self, search_results: str, search_type: str) -> str:
        """Extract sentiment insights from search results."""
        
        # Look for rating patterns (e.g., "4.5 stars", "4/5", "90%")
        rating_patterns = re.findall(r'(\d+\.?\d*)\s*(?:stars?|\/5|out of 5|%)', search_results.lower())
        
        # Look for sentiment keywords
        positive_keywords = ['excellent', 'great', 'amazing', 'love', 'fantastic', 'best', 'recommend', 'satisfied']
        negative_keywords = ['terrible', 'awful', 'hate', 'worst', 'scam', 'avoid', 'disappointed', 'poor']
        
        positive_count = sum(1 for word in positive_keywords if word in search_results.lower())
        negative_count = sum(1 for word in negative_keywords if word in search_results.lower())
        
        # Build summary based on search type
        if search_type == "customer_reviews":
            if rating_patterns:
                avg_rating = sum(float(r[0]) for r in rating_patterns[:5]) / min(len(rating_patterns), 5)
                return f"Found ratings averaging around {avg_rating:.1f}. Sentiment appears {'positive' if avg_rating > 3.5 else 'mixed' if avg_rating > 2.5 else 'negative'}."
            return "Review data found but specific ratings not clearly visible in search results."
            
        elif search_type in ["positive_sentiment", "negative_sentiment"]:
            if positive_count > negative_count:
                return f"Predominantly positive sentiment with {positive_count} positive indicators found."
            elif negative_count > positive_count:
                return f"Some negative sentiment detected with {negative_count} concerning indicators."
            else:
                return "Mixed sentiment signals in search results."
                
        elif search_type == "reddit_discussions":
            if "no results" in search_results.lower() or not search_results.strip():
                return "Limited or no discussions found on Reddit."
            return "Found discussions on Reddit. Manual review recommended for detailed sentiment."
            
        elif search_type == "employee_sentiment":
            if "glassdoor" in search_results.lower():
                return "Glassdoor presence detected. Employee reviews available for analysis."
            return "Limited employee sentiment data found in search results."
            
        else:
            return f"Search returned results. Manual analysis recommended for detailed insights."
    
    def _generate_overall_assessment(self, findings: List[Dict]) -> str:
        """Generate an overall assessment based on all findings."""
        
        assessment_parts = []
        
        # Check what we actually found
        has_reviews = any(f["search_type"] == "customer_reviews" for f in findings)
        has_social = any(f["search_type"] in ["reddit_discussions", "twitter_mentions"] for f in findings)
        has_employee = any(f["search_type"] == "employee_sentiment" for f in findings)
        
        positive_signals = sum(1 for f in findings if "positive" in f.get("summary", "").lower())
        negative_signals = sum(1 for f in findings if "negative" in f.get("summary", "").lower() or "concern" in f.get("summary", "").lower())
        
        # Build assessment
        if positive_signals > negative_signals:
            assessment_parts.append("Overall sentiment appears to be generally positive based on available data.")
        elif negative_signals > positive_signals:
            assessment_parts.append("Some negative sentiment indicators detected that warrant further investigation.")
        else:
            assessment_parts.append("Mixed sentiment signals found across different platforms.")
        
        # Note data availability
        if not has_reviews:
            assessment_parts.append("Limited formal review data available - company may be early-stage or B2B focused.")
        if not has_social:
            assessment_parts.append("Limited social media presence detected - consider the company's target market and stage.")
        if has_employee:
            assessment_parts.append("Employee sentiment data available for culture assessment.")
        
        return " ".join(assessment_parts)
    
    def _format_results(self, results: Dict) -> str:
        """Format results as a readable report."""
        output = []
        output.append(f"# Customer Sentiment Analysis for {results['company']}")
        output.append(f"Analysis Date: {results['analysis_date']}")
        output.append("")
        
        # Platforms searched
        output.append("## Platforms Searched")
        output.append(f"Attempted to gather data from: {', '.join(results['platforms_searched'])}")
        output.append("")
        
        # Key Findings
        output.append("## Search Results Summary")
        for finding in results["findings"]:
            output.append(f"\n### {finding['search_type'].replace('_', ' ').title()}")
            output.append(f"- Query: `{finding['query']}`")
            output.append(f"- Platforms: {', '.join(finding['platforms'])}")
            output.append(f"- Summary: {finding['summary']}")
        output.append("")
        
        # Overall Assessment
        output.append("## Overall Assessment")
        output.append(results["overall_assessment"])
        output.append("")
        
        # Limitations
        if results["limitations"]:
            output.append("## Data Limitations")
            for limitation in results["limitations"]:
                output.append(f"- {limitation}")
            output.append("")
        
        # Important Note
        output.append("## Important Note")
        output.append("This analysis is based on publicly available web search results. For comprehensive sentiment analysis:")
        output.append("- Direct API access to social platforms would provide more detailed data")
        output.append("- Consider using specialized sentiment analysis services")
        output.append("- Manual review of specific reviews and discussions is recommended")
        output.append("- Results may be limited for private companies or B2B-focused businesses")
        
        return "\n".join(output)