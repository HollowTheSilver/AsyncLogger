# AsyncLogger: Advanced Asynchronous Logging Framework

## Project Overview

AsyncLogger is an enterprise-grade logging framework engineered to address the complex logging requirements of modern Python applications. Designed with performance and security at its core, the library provides a robust, asynchronous logging solution that seamlessly integrates advanced data protection mechanisms with flexible configuration options.

The framework empowers developers to implement comprehensive logging strategies with minimal computational overhead, ensuring critical application insights are captured efficiently and securely across diverse computing environments.

## 🌟 Key Differentiators

### Comprehensive Logging Capabilities
- **Fully Asynchronous Design**: Zero-blocking log operations
- **Advanced Security Mechanisms**: Comprehensive protection against log injection
- **Intelligent Log Management**: Automatic file rotation and sanitization
- **Flexible Configuration**: Highly customizable logging behavior

## 🛠 Installation and Setup

### Prerequisites
- Python 3.9+
- `asyncio` library
- Minimal external dependencies

### Installation Methods

#### Direct from GitHub (Recommended for Development)
```bash
# Clone the repository
git clone https://github.com/HollowTheSilver/AsyncLogger.git

# Navigate to the project directory
cd AsyncLogger

# Install in editable mode
pip install -e .
```

#### Local Installation
```bash
# Clone the repository
git clone https://github.com/HollowTheSilver/AsyncLogger.git

# Navigate to the project directory
cd AsyncLogger

# Install dependencies
pip install -r requirements.txt
```

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest
```

## 💻 Usage Examples

### Basic Logging

```python
import asyncio
from asyncLogger import AsyncLogger
import logging

async def main():
    # Initialize logger with custom configuration
    logger = await AsyncLogger.create(
        name="ApplicationLogger",
        log_dir="logs",
        color_enabled=True,
        level=logging.INFO,
        max_bytes=5_242_880,  # 5 MB log file size
        backup_count=3
    )

    try:
        # Log messages with additional context
        await logger.info(
            "Application startup", 
            extras={
                "version": "1.0.0",
                "environment": "production"
            }
        )

        # Complex logging scenarios
        await logger.warning(
            "Resource utilization alert",
            extras={
                "cpu_usage": "85%",
                "memory_usage": "72%"
            }
        )

    except Exception as e:
        await logger.error(
            "Unexpected error occurred", 
            extras={"error_details": str(e)}
        )
    
    finally:
        await logger.shutdown()

asyncio.run(main())
```

## 🔧 Configuration Options

### Comprehensive Configuration Parameters

| Parameter | Type | Description | Default Value |
|-----------|------|-------------|---------------|
| `name` | `str` | Unique logger identifier | Required |
| `log_dir` | `str/Path` | Directory for log file storage | `None` |
| `console_format` | `str` | Custom console log message format | Predefined template |
| `file_format` | `str` | Custom file log message format | Predefined template |
| `color_enabled` | `bool` | Console color output | Auto-detect |
| `level` | `int` | Minimum logging severity level | `logging.DEBUG` |
| `max_bytes` | `int` | Maximum log file size | 10,485,760 (10 MB) |
| `backup_count` | `int` | Number of rotated log files | 5 |

## 📊 Monitoring and Diagnostics

### Health Tracking Methods

- `get_health_status()`: Retrieve comprehensive logger metrics
- `get_failed_logs()`: Access logs that failed processing
- `shutdown()`: Gracefully terminate logging operations

### Metrics Captured
- Total messages processed
- Error count
- Last error timestamp
- Batch processing statistics
- Extras cache performance

## 🛡️ Security Features

1. **Message Sanitization**
   - Strips control characters
   - Prevents log injection
   - Truncates oversized messages

2. **Extras Processing**
   - Validates and sanitizes additional context data
   - Masks potentially sensitive information
   - Enforces strict key and value length limits

3. **Error Resilience**
   - Captures failed log entries
   - Provides detailed error tracking
   - Prevents logging process from disrupting main application

## 🔬 Performance Considerations

- Minimal runtime overhead
- Asynchronous design prevents blocking
- Intelligent caching mechanisms
- Configurable batch processing
- Low memory footprint

## 📝 Logging Best Practices

1. Use appropriate log levels
2. Include meaningful context in log entries
3. Avoid logging sensitive information
4. Configure log rotation to manage disk space
5. Implement proper error handling

## 🤝 Contribution Guidelines

### How to Contribute
- Fork the repository
- Create a feature branch
- Submit pull requests
- Follow PEP 8 style guidelines
- Include comprehensive tests

## 📋 Compatibility

- Python 3.9+
- Cross-platform support (Windows, macOS, Linux)
- Compatible with major async frameworks

## 📦 Dependency Requirements

- Python standard library
- `asyncio`
- Minimal external dependencies

## 🔖 Versioning

Semantic Versioning (SemVer) used:
- Major version: Significant, potentially breaking changes
- Minor version: New features, backwards-compatible
- Patch version: Bug fixes and minor improvements

## 📄 License

Copyright © HollowTheSilver 2024-2025
Open-source license (MIT/Apache recommended)

## 📞 Support

- GitHub Issues: Report bugs, request features
- Email: hollowstools@gmail.com

## 🌐 Project Links

- GitHub Repository: https://github.com/HollowTheSilver/AsyncLogger/
- Documentation: https://github.com/HollowTheSilver/AsyncLogger/wiki

---

**Disclaimer**: AsyncLogger is continually evolving. Always refer to the latest documentation and release notes.
