from typing import List, Optional, Annotated
from pydantic import BaseModel, HttpUrl, Field


class OrganizerFeedback(BaseModel):
    feedback: str = Field(..., description="Feedback on the data quality and completeness")
    is_acceptable: bool = Field(..., description="Whether the organized data is acceptable or needs re-processing")

class OrganizedData(BaseModel):
    data: dict = Field(..., description="Organized company data in structured JSON format")

class FounderNames(BaseModel):
    names: Annotated[List[str], Field(description="List of the full names of the company founders.")] = None

class Founder(BaseModel):
    name: Annotated[str, Field(description="Full name of the founder")]
    role: Annotated[Optional[str], Field(description="Current role/title in the startup")] = None
    background: Annotated[Optional[str], Field(description="Narrative background summary")] = None
    education: Annotated[Optional[List[str]], Field(description="Education history")] = None
    work_experience: Annotated[Optional[List[str]], Field(description="Notable work experience")] = None
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


    
