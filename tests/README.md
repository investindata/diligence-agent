# Diligence Agent Tests

This directory contains the test suite for the Diligence Agent project.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Shared fixtures and pytest configuration
├── fixtures/                # Test data and sample files
│   └── sample_company.json  # Sample company data for testing
├── test_input_reader.py    # Tests for input reader module
├── test_progress_reporter.py # Tests for progress reporter
├── test_google_doc_processor.py # Tests for Google Doc processor
└── test_main.py            # Tests for main module
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Running All Tests

```bash
# Using the test runner script
./run_tests.sh

# Or using pytest directly
pytest tests/
```

### Running Specific Test Categories

```bash
# Run only unit tests (no integration)
./run_tests.sh unit

# Run integration tests
./run_tests.sh integration

# Run all tests with coverage
./run_tests.sh all

# Run fast tests only
./run_tests.sh fast
```

### Running Individual Test Files

```bash
# Test a specific module
pytest tests/test_input_reader.py -v

# Test a specific test class
pytest tests/test_progress_reporter.py::TestProgressReporter -v

# Test a specific test method
pytest tests/test_progress_reporter.py::TestProgressReporter::test_initialization -v
```

## Test Coverage

To generate a coverage report:

```bash
# Generate terminal coverage report
pytest tests/ --cov=src/diligence_agent --cov-report=term

# Generate HTML coverage report
pytest tests/ --cov=src/diligence_agent --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Markers

Tests are marked with the following markers for selective execution:

- `@pytest.mark.integration` - Tests that require external resources
- `@pytest.mark.slow` - Tests that take a long time to run
- `@pytest.mark.network` - Tests that require network access

Run tests by marker:
```bash
# Run only integration tests
pytest -m integration

# Run all except integration tests
pytest -m "not integration"

# Run tests that don't require network
pytest -m "not network"
```

## Writing New Tests

### Basic Test Structure

```python
import pytest
from unittest.mock import patch, MagicMock

class TestMyModule:
    def setup_method(self):
        """Set up test fixtures."""
        self.my_object = MyClass()
    
    def test_my_feature(self):
        """Test description."""
        result = self.my_object.my_method()
        assert result == expected_value
    
    @pytest.mark.integration
    def test_integration_feature(self):
        """Integration test requiring external resources."""
        # Test code here
```

### Using Fixtures

Fixtures are defined in `conftest.py` and can be used in any test:

```python
def test_with_fixture(sample_company_data):
    """Test using the sample_company_data fixture."""
    assert sample_company_data["company_name"] == "TestCorp"
```

## Continuous Integration

Tests are automatically run on:
- Every push to the repository
- Every pull request
- Nightly builds

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure the virtual environment is activated
2. **Missing dependencies**: Run `pip install -r requirements-test.txt`
3. **Network tests failing**: Some tests require internet access
4. **Google Doc tests failing**: Ensure test documents are accessible

### Debug Mode

Run tests with verbose output and full traceback:
```bash
pytest tests/ -vv --tb=long
```

Run with debug logging:
```bash
pytest tests/ --log-cli-level=DEBUG
```