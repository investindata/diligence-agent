from typing import List, Optional, Annotated
from pydantic import BaseModel, HttpUrl, Field


class WorkExperience(BaseModel):
    company: str = Field(..., description="Company name")
    role: Optional[str] = Field(None, description="Role/position held")
    years: Optional[str] = Field(None, description="Time period (e.g., '2020-2023' or 'Present')")

class OrganizedData(BaseModel):
    data: dict = Field(..., description="Organized company data in structured JSON format")

class FounderBackground(BaseModel):
    name: Annotated[str, Field(description="Full name of the founder")] = ""
    pronoumns: Annotated[Optional[str], Field(description="Pronoums used to address the founder")] = None
    role: Annotated[Optional[str], Field(description="Current role/title in the startup")] = None
    background: Annotated[Optional[str], Field(description="Narrative background summary")] = None
    education: Annotated[Optional[List[str]], Field(description="Education history")] = None
    work_experience: Annotated[Optional[List[WorkExperience]], Field(description="Notable work experience")] = None
    notable_achievements: Annotated[Optional[List[str]], Field(description="Key achievements, awards, or exits")] = None
    track_record: Annotated[Optional[str], Field(description="Track record in prior ventures or roles")] = None
    red_flags: Annotated[Optional[List[str]], Field(description="Potential concerns or risks related to this founder")] = None
    linkedin_url: Annotated[Optional[HttpUrl], Field(description="Link to LinkedIn profile")] = None
    other_profiles: Annotated[Optional[List[HttpUrl]], Field(description="Other relevant online profiles (GitHub, AngelList, etc.)")] = None


class Founders(BaseModel):
    founders: Annotated[List[FounderBackground], Field(description="List of all founders")] = []
    overall_assessment: Annotated[Optional[str], Field(description="Synthesis of the founding team as a whole")] = None
    strengths: Annotated[Optional[List[str]], Field(description="Key strengths across the founding team")] = None
    risks: Annotated[Optional[List[str]], Field(description="Key risks across the founding team")] = None


class Competitor(BaseModel):
    name: str = Field("", description="Name of the competitor company")
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
    direct_competitors: List[Competitor] = Field([], description="Companies offering highly similar products/services targeting the same market")
    indirect_competitors: Optional[List[Competitor]] = Field(None, description="Companies offering alternative or adjacent solutions")
    emerging_competitors: Optional[List[Competitor]] = Field(None, description="New entrants or startups showing traction in the space")
    substitutes: Optional[List[str]] = Field(None, description="Alternative solutions that address the same customer need but differently")
    barriers_to_entry: Optional[List[str]] = Field(None, description="Factors that make it difficult for new competitors to enter the space")
    overall_analysis: Optional[str] = Field(None, description="Analyst-style summary of the competitive landscape, highlighting opportunities and threats")
    positioning_summary: Optional[str] = Field(None, description="How the target company is positioned relative to competitors")


class MarketSegment(BaseModel):
    name: str = Field("", description="Name of the market segment, e.g., 'SMB SaaS', 'Healthcare AI'")
    description: Optional[str] = Field(None, description="Brief description of the segment and its characteristics")
    size: Optional[str] = Field(None, description="Estimated size of the segment, e.g., '$10B in 2024'")
    growth_rate: Optional[str] = Field(None, description="Expected CAGR or annual growth rate")
    key_drivers: Optional[List[str]] = Field(None, description="Main factors driving growth in this segment")
    key_challenges: Optional[List[str]] = Field(None, description="Challenges or barriers in this segment")
    customer_types: Optional[List[str]] = Field(None, description="Types of customers in this segment, e.g., enterprises, SMBs, governments")


class Market(BaseModel):
    total_addressable_market: Optional[str] = Field(None, description="Size of the global market opportunity (TAM)")
    serviceable_available_market: Optional[str] = Field(None, description="Portion of TAM the company can serve (SAM)")
    serviceable_obtainable_market: Optional[str] = Field(None, description="Realistic market share the company could capture (SOM)")
    segments: Optional[List[MarketSegment]] = Field(None, description="Breakdown of key market segments")
    trends: Optional[List[str]] = Field(None, description="Important market trends shaping the opportunity")
    risks: Optional[List[str]] = Field(None, description="Risks or uncertainties affecting the market")
    major_geographies: Optional[List[str]] = Field(None, description="Key regions or countries where the market is concentrated")
    overall_summary: Optional[str] = Field(None, description="Concise narrative summarizing the market opportunity and dynamics")


class ProductFeature(BaseModel):
    name: str = Field("", description="Name of the feature")
    description: Optional[str] = Field(None, description="Brief description of what the feature does")
    differentiation: Optional[str] = Field(None, description="How this feature stands out vs competitors")


class Product(BaseModel):
    name: Optional[str] = Field(None, description="Name of the product")
    description: Optional[str] = Field(None, description="Overview of what the product is and does")
    target_users: Optional[List[str]] = Field(None, description="Target personas or customer segments")
    use_cases: Optional[List[str]] = Field(None, description="Key use cases the product enables")
    features: Optional[List[ProductFeature]] = Field(None, description="List of main features with differentiation")
    technology_stack: Optional[List[str]] = Field(None, description="Technologies used to build the product")
    integrations: Optional[List[str]] = Field(None, description="3rd party systems the product integrates with")
    pricing_model: Optional[str] = Field(None, description="Pricing structure, e.g., SaaS subscription, per-seat, usage-based")
    distribution_channels: Optional[List[str]] = Field(None, description="Ways the product is distributed, e.g., direct sales, marketplace, resellers")
    adoption_metrics: Optional[List[str]] = Field(None, description="Key adoption or traction numbers, e.g., users, customers, ARR")
    roadmap: Optional[List[str]] = Field(None, description="Planned future features or directions")
    intellectual_property: Optional[List[str]] = Field(None, description="Patents or proprietary assets")
    website: Optional[str] = Field(None, description="Official website URL")
    demo_or_docs: Optional[List[str]] = Field(None, description="Links to demo, product documentation, or videos")
    overall_summary: Optional[str] = Field(None, description="Concise narrative summarizing the product and positioning")


class WhyInteresting(BaseModel):
    unique_insight: Optional[str] = Field(None, description="Proprietary or contrarian insight the founders bring")
    team_strength: Optional[List[str]] = Field(None, description="Reasons why the team is exceptional, e.g., repeat founders, deep expertise")
    timing_factors: Optional[List[str]] = Field(None, description="Why now is the right time, e.g., market shifts, regulation, enabling tech")
    technology_moat: Optional[List[str]] = Field(None, description="Sources of defensibility, e.g., proprietary data, algorithms, IP")
    early_signs_of_traction: Optional[List[str]] = Field(None, description="Initial customers, pilots, growth metrics, partnerships")
    market_tailwinds: Optional[List[str]] = Field(None, description="Macro or industry trends driving demand")
    scalability_potential: Optional[str] = Field(None, description="How the company can scale to capture a large TAM")
    competitive_angle: Optional[str] = Field(None, description="How the company differentiates from incumbents or startups")
    investor_fit: Optional[str] = Field(None, description="Why the startup aligns with an early-stage investor's thesis")
    red_flags: Optional[List[str]] = Field(None, description="Risks or concerns that might offset the opportunity")
    overall_summary: Optional[str] = Field(None, description="Concise narrative: why this company is interesting for investors")

class CompanyOverview(BaseModel):
    name: str = Field("", description="The official name of the company.")
    location: Optional[str] = Field(None, description="Headquarters location (city, state, country).")
    founding_year: Optional[int] = Field(None, description="Year the company was founded.")
    stage: Optional[str] = Field(None, description="Company stage (e.g., pre-seed, seed, Series A, growth).")
    mission: Optional[str] = Field(None, description="Short statement of the company's mission or vision.")
    description: Optional[str] = Field(None, description="Brief overview of what the company does and its value proposition.")
    key_milestones: Optional[list[str]] = Field(
        None, description="List of notable milestones (e.g., product launches, funding rounds, partnerships)."
    )

class ReportConclusion(BaseModel):
    key_strengths: list[str] = Field(
        [], description="List of the company's most compelling strengths (e.g., strong founding team, differentiated technology)."
    )
    key_risks: list[str] = Field(
        [], description="List of risks or concerns (e.g., competitive pressure, regulatory uncertainty, unclear business model)."
    )
    investment_thesis: Optional[str] = Field(
        None, description="Summary of why this company is interesting or not as an investment opportunity."
    )
    open_questions: Optional[list[str]] = Field(
        None, description="Outstanding questions or areas requiring further diligence before making an investment decision."
    )
    recommendation: Optional[str] = Field(
        None, description="Overall recommendation (e.g., proceed with diligence, pass, or monitor)."
    )


class ReportStructure(BaseModel):
    company_overview_section: str = Field("", description="High-level overview of the company: what it does, stage, location, and core mission.")
    product_section: str = Field("", description="Detailed description of the product or service: features, differentiation, technology stack, adoption, and roadmap.")
    why_interesting_section: str = Field("", description="Analysis of why the company is compelling from an early-stage investment perspective: team, timing, traction, market tailwinds, and defensibility.")
    founders_section: str = Field("", description="Profiles of the founders: background, track record, education, notable achievements, red flags, and links to professional profiles.")
    competitive_landscape_section: str = Field("", description="Assessment of the competitive landscape: direct competitors, indirect competitors, substitutes, market positioning, and differentiation factors.")
    market_section: str = Field("", description="Analysis of the market opportunity: TAM/SAM/SOM, key segments, trends, risks, customer types, and major geographies.")
    report_conclusion_section: str = Field("", description="Final investment-oriented summary: key strengths, risks, and a recommendation or open questions for further diligence.")

