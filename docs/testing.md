# Testing Guide for Discord Overseerr Bot

## Overview

This project includes a comprehensive test suite with unit tests and integration tests to ensure code quality and reliability.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Shared fixtures and test configuration
├── test_settings.py            # Settings and configuration tests
├── test_overseerr.py           # Overseerr API client tests
├── test_notifications.py       # Notification manager tests
├── test_main.py                # Main bot functionality tests
└── test_integration.py         # Integration and end-to-end tests
```

## Running Tests

### Install Test Dependencies

```bash
# Using uv (recommended)
uv pip install -r requirements.txt

# Or using pip
pip install -r requirements.txt
```

### Run All Tests

```bash
# Run all tests with coverage
pytest

# Run tests verbosely
pytest -v

# Run with detailed output
pytest -vv
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run tests from a specific file
pytest tests/test_overseerr.py

# Run a specific test class
pytest tests/test_overseerr.py::TestOverseerrClient

# Run a specific test function
pytest tests/test_overseerr.py::TestOverseerrClient::test_client_creation
```

### Run Tests with Coverage Report

```bash
# Generate coverage report in terminal
pytest --cov=bot --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=bot --cov-report=html

# Open HTML coverage report (on macOS)
open htmlcov/index.html
```

### Watch Mode (Continuous Testing)

```bash
# Install pytest-watch
pip install pytest-watch

# Run tests on file changes
ptw
```

## Test Markers

Tests are organized with pytest markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (test component interactions)
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.requires_discord` - Tests requiring Discord API
- `@pytest.mark.requires_overseerr` - Tests requiring Overseerr API

## Writing New Tests

### Example Unit Test

```python
import pytest
from bot.overseerr import Movie, MediaStatus

@pytest.mark.unit
class TestMovie:
    def test_movie_creation(self):
        """Test creating a Movie instance"""
        movie = Movie(
            tmdb_id=550,
            title="Fight Club",
            overview="Test overview",
            release_date="1999-10-15",
            poster_path="/test.jpg",
        )
        
        assert movie.tmdb_id == 550
        assert movie.title == "Fight Club"
```

### Example Integration Test

```python
import pytest
from bot.main import MovieBot

@pytest.mark.integration
@pytest.mark.asyncio
async def test_bot_initialization(settings_manager):
    """Test bot initialization"""
    bot = MovieBot(settings_manager)
    
    # Test setup logic
    await bot.setup_hook()
    
    assert bot.overseerr is not None
    assert bot.notifications is not None
```

## Fixtures

Common fixtures available in `tests/conftest.py`:

- `mock_env_vars` - Mock environment variables
- `temp_config_dir` - Temporary directory for config files
- `bot_settings` - BotSettings instance with test data
- `settings_manager` - SettingsManager instance
- `overseerr_client` - OverseerrClient instance
- `mock_discord_bot` - Mock Discord bot
- `mock_discord_interaction` - Mock Discord interaction
- `sample_movie` - Sample Movie object
- `sample_tv_show` - Sample TVShow object
- `overseerr_search_response` - Mock Overseerr API search response

## Code Coverage Goals

- **Overall Coverage**: > 80%
- **Critical Modules**: > 90%
  - `bot/settings.py`
  - `bot/overseerr.py`
  - `bot/notifications.py`

## Best Practices

### 1. Test Naming

Use descriptive test names that explain what is being tested:

```python
def test_movie_poster_url_when_poster_path_is_none():
    """Good: Clear what scenario is being tested"""
    pass

def test_movie():
    """Bad: Unclear what is being tested"""
    pass
```

### 2. Arrange-Act-Assert Pattern

```python
def test_add_request():
    # Arrange - Set up test data
    manager = NotificationManager(bot, "test.json")
    
    # Act - Perform the action
    manager.add_request(111, "TestUser", 550, "Fight Club")
    
    # Assert - Verify the result
    assert len(manager.pending_requests) == 1
```

### 3. Use Fixtures for Common Setup

```python
@pytest.fixture
def movie_manager():
    return NotificationManager(mock_bot, "test.json")

def test_add_request(movie_manager):
    # Fixture provides the manager
    movie_manager.add_request(111, "User", 550, "Movie")
    assert len(movie_manager.pending_requests) == 1
```

### 4. Mock External Dependencies

```python
@pytest.mark.asyncio
async def test_overseerr_search(overseerr_client):
    with aioresponses() as m:
        # Mock the HTTP response
        m.get(
            f"{overseerr_client.base_url}search",
            status=200,
            payload={"results": []}
        )
        
        results = await overseerr_client.search_media("test")
        assert isinstance(results, list)
```

### 5. Test Edge Cases

```python
def test_elapsed_time_singular():
    """Test singular units (1 hour, not 1 hours)"""
    pass

def test_elapsed_time_plural():
    """Test plural units (2 hours)"""
    pass

def test_elapsed_time_zero():
    """Test zero values"""
    pass
```

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pytest --cov=bot --cov-report=xml
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Debugging Tests

### Run with pdb on failure

```bash
pytest --pdb
```

### Show print statements

```bash
pytest -s
```

### Show locals on failure

```bash
pytest --showlocals
```

### Run last failed tests only

```bash
pytest --lf
```

### Run tests in parallel (faster)

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run with 4 workers
pytest -n 4
```

## Troubleshooting

### ImportError: No module named 'bot'

Make sure you're running pytest from the project root directory.

### Session/Event Loop Warnings

These are handled by `pytest-asyncio`. Ensure `asyncio_mode = auto` is set in `pytest.ini`.

### Fixture Not Found

Check that `conftest.py` is in the `tests/` directory and the fixture is defined there.

### Coverage Not Showing All Files

Ensure `source = bot` is set in the `[coverage:run]` section of `pytest.ini`.

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [aioresponses Documentation](https://github.com/pnuckowski/aioresponses)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
