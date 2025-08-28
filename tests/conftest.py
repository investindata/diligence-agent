"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def sample_company_data():
    """Provide sample company data for tests."""
    return {
        "company_name": "TestCorp",
        "company_sources": [
            "https://docs.google.com/document/d/test123/edit",
            "TestCorp is a leading AI company.",
            "We provide ML infrastructure solutions."
        ],
        "reference_sources": [
            "https://example.com/reference",
            "Market research report"
        ],
        "current_date": "2025-01-27"
    }


@pytest.fixture
def temp_data_dir(sample_company_data):
    """Create a temporary data directory with test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_path = Path(temp_dir)
        
        # Create sample company files
        companies = [
            ("testcorp.json", sample_company_data),
            ("company2.json", {
                **sample_company_data,
                "company_name": "Company2"
            }),
            ("company3.json", {
                **sample_company_data,
                "company_name": "Company3"
            })
        ]
        
        for filename, data in companies:
            file_path = data_path / filename
            with open(file_path, 'w') as f:
                json.dump(data, f)
        
        yield str(data_path)


@pytest.fixture
def mock_crew():
    """Mock DiligenceAgent crew for testing."""
    mock_crew_instance = MagicMock()
    mock_crew_obj = MagicMock()
    mock_crew_obj.kickoff.return_value = "Analysis complete"
    mock_crew_instance.crew.return_value = mock_crew_obj
    return mock_crew_instance


@pytest.fixture
def mock_progress_reporter():
    """Mock progress reporter for testing."""
    mock_reporter = MagicMock()
    mock_reporter.__enter__ = MagicMock(return_value=mock_reporter)
    mock_reporter.__exit__ = MagicMock(return_value=None)
    return mock_reporter


@pytest.fixture(autouse=True)
def cleanup_task_outputs():
    """Clean up task_outputs directory after tests."""
    yield
    # Clean up any task_outputs directory created during tests
    task_outputs = Path("task_outputs")
    if task_outputs.exists():
        import shutil
        shutil.rmtree(task_outputs)


@pytest.fixture
def mock_google_doc():
    """Mock Google Doc content for testing."""
    return """
    # TestCorp Due Diligence Report
    
    ## Overview
    TestCorp is an innovative AI company.
    
    ## Product
    We offer cutting-edge ML infrastructure.
    
    ## Market
    The AI market is growing rapidly.
    
    ## Team
    Our team consists of experienced engineers.
    """


# Markers for different test types
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "network: mark test as requiring network access"
    )