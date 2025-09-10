from crewai import Agent
from crewai.llm import LLM
from crewai_tools import SerperDevTool, SerperScrapeWebsiteTool
from src.diligence_agent.tools.simple_auth_helper import SimpleLinkedInAuthTool



#model = "gpt-4o-mini"
model = "gpt-4.1-mini"
#model = "gpt-5-nano"
#model = "gemini/gemini-1.5-flash"
#model = "gemini/gemini-2.0-flash"
#model = "gemini/gemini-2.5-flash"

import os

llm = LLM(
    model=model,
    #api_key=os.getenv("GOOGLE_API_KEY"),
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.0,
)

organizer_agent = Agent(
    role="Data organizer",
    goal="Organize unstructured data into a clean format.",
    backstory="You are an excellent data organizer with strong attention to detail.",
    verbose=False,
    llm=llm,
    max_iter=8,
)

search_agent = Agent(
    role="Web Search Researcher",
    goal="Search the web for valuable information about a topic.",
    backstory="You are an excellent researcher who can search the web using Serper.",
    verbose=False,
    llm=llm,
    max_iter=8,
    tools=[SerperDevTool()],
)

scraper_agent = Agent(
    role="Web Scraper Researcher",
    goal="Scrape the web for valuable information about a topic using both search engines and browser automation.",
    backstory="You are an excellent researcher who can navigate websites using Playwright for thorough information gathering.",
    verbose=False,
    llm=llm,
    max_iter=15,
    tools=[SerperScrapeWebsiteTool()]
)

writer_agent = Agent(
    role="Writer",
    goal="Synthesize and write a comprehensive report based on gathered research.",
    backstory="You are an expert writer who can create clear, concise, and well-structured reports.",
    verbose=False,
    llm=llm,
    max_iter=5,
)