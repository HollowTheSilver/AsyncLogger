import pytest
import asyncio
import logging
import tempfile
from pathlib import Path
from . import AsyncLogger


@pytest.fixture(scope="function")
def event_loop():
    """Create an event loop for each test case."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def test_dir():
    """Create a temporary directory for test logs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def logger(test_dir, event_loop):
    """Create a logger instance for testing."""
    logger_instance = event_loop.run_until_complete(
        AsyncLogger.create(
            name="test_logger",
            log_dir=Path(test_dir),
            level=logging.DEBUG
        )
    )
    yield logger_instance
    event_loop.run_until_complete(logger_instance.shutdown())


@pytest.mark.asyncio
async def test_logger_creation(logger: AsyncLogger):
    """Test basic logger creation and initialization."""
    assert logger is not None
    assert logger.logger.name == "test_logger"
    assert len(logger.logger.handlers) > 0


@pytest.mark.asyncio
async def test_basic_logging(logger: AsyncLogger):
    """Test basic logging functionality."""
    message = "Test log message"
    await logger.info(message)
    assert logger.metrics.total_messages == 1
    assert logger.metrics.error_count == 0


@pytest.mark.asyncio
async def test_logging_with_extras(logger: AsyncLogger):
    """Test logging with extra fields."""
    extras = {"test_key": "test_value"}
    await logger.info("Test message", extras=extras)
    assert logger.metrics.total_messages == 1


@pytest.mark.asyncio
async def test_error_handling(logger: AsyncLogger):
    """Test error count increments properly."""
    await logger.log(logging.INFO, None)  # This should trigger the error handling
    # Check that an error was recorded
    assert logger.metrics.error_count == 1
    # Verify that there are failed log entries
    failed_logs = await logger.get_failed_logs()
    assert len(failed_logs) > 0
    # Optional: Check the content of the failed log entry
    assert failed_logs[-1].message == '[empty message]'


@pytest.mark.asyncio
async def test_invalid_level_handling(logger: AsyncLogger):
    """Test handling of invalid log levels."""
    await logger.log(-1, "Invalid level")
    assert logger.metrics.total_messages == 1
    # Verify the message was logged despite invalid level
    assert len(logger.logger.handlers) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
