# AsyncLogger Color Formatting Demo

## Overview
This interactive demo showcases the powerful color and styling capabilities of AsyncLogger's logging system.

## Prerequisites
- Python 3.9+
- AsyncLogger library installed
- Terminal/Command Prompt

## Installation
1. Ensure AsyncLogger is installed:
   ```bash
   pip install asynclogger
   ```

2. Navigate to the demo directory:
   ```bash
   cd demos/color_formatting
   ```

## Running the Demo
Execute the demo script:
```bash
python color_demo.py
```

## Demo Features
- Interactive color selection
- Multiple color categories
- Style combination options
- Real-time log message formatting preview

## How to Use
1. Select a color category (basic, dark, bright, etc.)
2. Choose a specific color or style
3. Optionally combine multiple styles
4. View the generated log message format
5. Continue exploring or exit the demo

## Example Usage in Code
```python
# Using color tags in AsyncLogger
await logger.info("<RED><BOLD>Critical system event</BOLD></RED>")
await logger.warning("<YELLOW>Performance warning</YELLOW>")
```

## Compatibility
- Works with AsyncLogger v1.0.0+
- Supports all major operating systems

## Troubleshooting
- Ensure AsyncLogger is properly installed
- Check Python version compatibility
- Verify terminal/command prompt support for ANSI colors

## Contributing
Feedback and contributions are welcome! Please open an issue in the main AsyncLogger repository.