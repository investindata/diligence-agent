from typing import List, Optional, Annotated
from pydantic import BaseModel, HttpUrl, Field


class WorkExperience(BaseModel):
    company: str = Field(..., description="Company name")
    role: Optional[str] = Field(None, description="Role/position held")
    years: Optional[str] = Field(None, description="Time period (e.g., '2020-2023' or 'Present')")

class OrganizedData(BaseModel):
    data: dict = Field(..., description="Organized company data in structured JSON format")

class FounderNames(BaseModel):
    names: Annotated[List[str], Field(description="List of the full names of the company founders.")] = None

class Founder(BaseModel):
    name: Annotated[str, Field(description="Full name of the founder")]
    role: Annotated[Optional[str], Field(description="Current role/title in the startup")] = None
    background: Annotated[Optional[str], Field(description="Narrative background summary")] = None
    education: Annotated[Optional[List[str]], Field(description="Education history")] = None
    work_experience: Annotated[Optional[List[WorkExperience]], Field(description="Notable work experience")] = None
    notable_achievements: Annotated[Optional[List[str]], Field(description="Key achievements, awards, or exits")] = None
    track_record: Annotated[Optional[str], Field(description="Track record in prior ventures or roles")] = None
    red_flags: Annotated[Optional[List[str]], Field(description="Potential concerns or risks related to this founder")] = None
    linkedin_url: Annotated[Optional[HttpUrl], Field(description="Link to LinkedIn profile")] = None
    other_profiles: Annotated[Optional[List[HttpUrl]], Field(description="Other relevant online profiles (GitHub, AngelList, etc.)")] = None


class FoundersSection(BaseModel):
    founders: Annotated[List[Founder], Field(description="List of all founders")]
    overall_assessment: Annotated[Optional[str], Field(description="Synthesis of the founding team as a whole")] = None
    strengths: Annotated[Optional[List[str]], Field(description="Key strengths across the founding team")] = None
    risks: Annotated[Optional[List[str]], Field(description="Key risks across the founding team")] = None


class Competitor(BaseModel):
    name: str = Field(..., description="Name of the competitor company")
    description: Optional[str] = Field(None, description="Brief description of the competitor’s business, product, or service")
    website: Optional[HttpUrl] = Field(None, description="Official website of the competitor")
    products_or_services: Optional[List[str]] = Field(None, description="List of notable products or services offered")
    target_customers: Optional[str] = Field(None, description="Target audience or customer segments")
    funding_stage: Optional[str] = Field(None, description="Known funding stage (e.g., seed, Series A, public)")
    market_share: Optional[str] = Field(None, description="Approximate market share or market presence")
    strengths: Optional[List[str]] = Field(None, description="Competitive advantages or differentiators")
    weaknesses: Optional[List[str]] = Field(None, description="Limitations, gaps, or weaknesses")
    notable_investors: Optional[List[str]] = Field(None, description="List of notable investors, if any")
    other_profiles: Optional[List[HttpUrl]] = Field(None, description="Links to profiles such as Crunchbase, LinkedIn, etc.")


class CompetitiveLandscape(BaseModel):
    direct_competitors: List[Competitor] = Field(..., description="Companies offering highly similar products/services targeting the same market")
    indirect_competitors: Optional[List[Competitor]] = Field(None, description="Companies offering alternative or adjacent solutions")
    emerging_competitors: Optional[List[Competitor]] = Field(None, description="New entrants or startups showing traction in the space")
    substitutes: Optional[List[str]] = Field(None, description="Alternative solutions that address the same customer need but differently")
    barriers_to_entry: Optional[List[str]] = Field(None, description="Factors that make it difficult for new competitors to enter the space")
    overall_analysis: Optional[str] = Field(None, description="Analyst-style summary of the competitive landscape, highlighting opportunities and threats")
    positioning_summary: Optional[str] = Field(None, description="How the target company is positioned relative to competitors")


class MarketSegment(BaseModel):
    name: str
    description: Optional[str] = None
    size: Optional[str] = None  # e.g., "$10B in 2024"
    growth_rate: Optional[str] = None  # e.g., "15% CAGR"
    key_drivers: Optional[List[str]] = None
    key_challenges: Optional[List[str]] = None
    customer_types: Optional[List[str]] = None

class Market(BaseModel):
    total_addressable_market: Optional[str] = None  # e.g., "$50B globally"
    serviceable_available_market: Optional[str] = None
    serviceable_obtainable_market: Optional[str] = None
    segments: Optional[List[MarketSegment]] = None
    trends: Optional[List[str]] = None  # e.g., "increasing demand for generative AI"
    risks: Optional[List[str]] = None  # e.g., "regulatory uncertainty"
    major_geographies: Optional[List[str]] = None  # e.g., "US, Europe, APAC"
    overall_summary: Optional[str] = None