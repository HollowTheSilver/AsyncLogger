"""
AsyncLogger Module
-----------------------------

Copyright © HollowTheSilver 2024-2025 - https://github.com/HollowTheSilver

Version: 1.0.0

Description:

The AsyncLogger module provides an advanced asynchronous logging framework
with support for colored console output, automatic log file rotation, structured
logging, and robust error handling. It offers an easy-to-use interface for adding
logging to asynchronous applications while addressing common challenges such as
log injection attacks and improper handling of sensitive data.

The AsyncLogger class enables logging to both the terminal and rotating log files
on disk. Console output can be enhanced with ANSI colors and styles to improve
readability. All logging operations are performed asynchronously to avoid blocking
the main application flow. The module automatically detects and masks sensitive
information in log messages and extra context data to prevent unintended data leakage.

Key Features:
- Asynchronous logging to console and files
- ANSI colors and styles for eye-catching console logs
- Automatic log file rotation based on configurable size limits
- Structured logging with custom fields
- Proper handling of exceptions during the logging process
- Automatic masking of sensitive information in log data
- Capturing of logger health metrics and error statistics
- Periodic flushing of logs to disk to ensure data persistence
- Convenience methods for logging at each severity level
- Ability to customize log formats and color schemes

Example Usage:
    ```python
    from asyncLogger import AsyncLogger

    async def main():
        logger = await AsyncLogger.create(
            name="ExampleApp",
            console_format="<green>{time}</green> {message}",
            file_format="{time} - {level}: {message}",
            log_dir="logs",
            color_enabled=True,
        )

        await logger.info("Application starting", extras={"version": "1.0.0"})

        try:
            # Application logic here
            ...
        except Exception as e:
            await logger.exception("Unhandled exception occurred", e)
        finally:
            await logger.info("Application shutting down")
            await logger.shutdown()
    ```
"""


# // ========================================( Modules )======================================== // #

import os
import re
import sys
import time
import inspect
import logging
import platform
import datetime
import asyncio
from enum import Enum
from dataclasses import dataclass
from collections import deque
from pathlib import Path
from logging.handlers import RotatingFileHandler
from asyncio import Lock as AsyncLock
from typing import Optional, Dict, List, Tuple, Any, Union, Literal, Deque


# // ========================================( Exceptions )======================================== // #


class LoggerError(Exception):
    """
    Base exception class for logger-specific errors.
    Inherits from the built-in Exception class.

    This exception can be raised for any general logger error that doesn't fit
    into a more specific exception category. It serves as the parent class for
    other custom logger exceptions.

    Example usage:
        try:
            # Some logger operation
        except LoggerError as e:
            print(f"A logger error occurred: {str(e)}")
    """
    pass


class LoggerConfigError(LoggerError):
    """
    Exception raised when logger configuration is invalid.
    Inherits from the custom LoggerError class.

    This exception indicates that an issue occurred during logger setup or
    configuration. It can encapsulate errors related to invalid parameters,
    file permissions, or system configuration problems that prevent the logger
    from being initialized correctly.

    Example usage:
        try:
            logger = AsyncLogger(name="InvalidLogger", log_dir=None)
        except LoggerConfigError as e:
            print(f"Logger configuration error: {str(e)}")
    """
    pass


@dataclass
class FailedLogEntry:
    """
    Represents a failed logging attempt.

    Encapsulates details about a log message that could not be successfully
    logged due to an error. The dataclass contains fields to store the timestamp,
    logging level, original message, and the error that prevented logging.

    Attributes:
        timestamp (datetime): The timestamp when the logging attempt failed.
        level (int): The log level (e.g. logging.ERROR) of the failed entry.
        message (str): The original log message that failed.
        error (str): Details about the error that prevented successful logging.

    Example usage:
        failed_entry = FailedLogEntry(
            timestamp=datetime.utcnow(),
            level=logging.CRITICAL,
            message="System out of memory",
            error="MemoryError: Allocation failed"
        )
        print(f"Log entry failed at {failed_entry.timestamp} with error {failed_entry.error}")
    """
    timestamp: datetime
    level: int
    message: str
    error: str


@dataclass
class LoggerMetrics:
    """
    Tracks metrics and statistics about logger usage and health.

    Provides a simple way to capture and surface important logger metrics
    such as the total number of messages logged, count of error logs, and
    the last error timestamp. Can be used for monitoring logger activity.

    Attributes:
        total_messages (int): Count of all log messages processed.
        error_count (int): Count of log messages that resulted in an error.
        last_error_time (float): Unix timestamp of the most recent error.

    Methods:
        record_message(): Increments the total messages counter.
        record_error(): Increments the error counter and sets last error time.

    Example usage:
        metrics = LoggerMetrics()
        metrics.record_message()
        print(f"Total messages logged: {metrics.total_messages}")
    """
    total_messages: int = 0
    error_count: int = 0
    last_error_time: Optional[float] = None

    def record_message(self) -> None:
        """
        Increments the total log messages counter.
        Call this whenever the logger sends a message to handlers.
        """
        self.total_messages += 1

    def record_error(self) -> None:
        """
        Tracks a message logging failure.
        Increments the error counter and stores the current timestamp.
        """
        self.error_count += 1
        self.last_error_time = time.time()


# // ========================================( Classes )======================================== // #


def detect_color_support() -> bool:
    """
    Determines if the current environment supports color output.
    Considers IDE overrides, system environment variables, and platform.

    Returns:
        bool: True if color output is likely supported, False otherwise.

    Detailed behavior:
    - Checks for common color-override environment variables used by IDEs and tools
    - Honors explicit NO_COLOR environment setting to disable color
    - Checks for popular editor/IDE env vars that indicate color support
    - Checks current platform (supports Windows, macOS, Linux)
    - Attempts to detect PyCharm Ipython environment
    - Returns False if any check fails or throws an exception

    Example usage:
        if detect_color_support():
            print("Color output enabled")
        else:
            print("Using plain monochrome output")
    """
    ide_indicators = [
        'PYCHARM_HOSTED', 'VSCODE_PID', 'TERM_PROGRAM',
        'INTELLIJ_ENVIRONMENT', 'RIDER_HOME', 'ECLIPSE_HOME'
    ]
    ide_detected = any(os.getenv(var) for var in ide_indicators)
    if os.getenv('FORCE_COLOR', '').lower() in ('1', 'true', 'yes'):
        return True
    if os.getenv('NO_COLOR'):
        return False
    try:
        if ide_detected:
            return True
        plat = platform.system().lower()
        if plat in ['windows', 'darwin', 'linux']:
            return True
        import importlib.util
        spec = importlib.util.find_spec('pydev_ipython_console')
        if spec is not None:
            return True
    except Exception:
        pass
    return False


class ANSIColors(Enum):
    """
    Defines ANSI color and style codes for decorating terminal output.

    An enum that maps readable color names to their ANSI escape codes. Provides
    a wide range of colors including dark and bright variants. Also defines basic
    text style codes like bold and underline.

    Includes a special RESET code to clear all active formatting.
    Uses 256-color codes for more refined and consistent color options.

    Usage:
        print(f"{ANSIColors.BOLD.value}Bold Text{ANSIColors.RESET.value}")
        print(f"{ANSIColors.GREEN.value}Green Text{ANSIColors.RESET.value}")

        # Combining multiple codes
        red_bold_text = (
            f"{ANSIColors.RED.value}{ANSIColors.BOLD.value}"
            f"Important Warning"
            f"{ANSIColors.RESET.value}"
        )
    """

    # Basic colors
    BLACK = "\x1b[30m"
    RED = "\x1b[31m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    BLUE = "\x1b[34m"
    MAGENTA = "\x1b[35m"
    CYAN = "\x1b[36m"
    WHITE = "\x1b[37m"
    GRAY = "\x1b[90m"

    # Dark colors (using 256-color codes for better gradation)
    DARK_RED = "\x1b[38;5;88m"
    DARK_GREEN = "\x1b[38;5;22m"
    DARK_YELLOW = "\x1b[38;5;58m"
    DARK_BLUE = "\x1b[38;5;18m"
    DARK_MAGENTA = "\x1b[38;5;90m"
    DARK_CYAN = "\x1b[38;5;23m"
    DARK_GRAY = "\x1b[38;5;240m"

    # Bright colors
    BRIGHT_RED = "\x1b[91m"
    BRIGHT_GREEN = "\x1b[92m"
    BRIGHT_YELLOW = "\x1b[93m"
    BRIGHT_BLUE = "\x1b[94m"
    BRIGHT_MAGENTA = "\x1b[95m"
    BRIGHT_CYAN = "\x1b[96m"
    BRIGHT_WHITE = "\x1b[97m"

    # Muted colors (using 256-color codes for better gradation)
    MUTED_RED = "\x1b[38;5;131m"
    MUTED_GREEN = "\x1b[38;5;108m"
    MUTED_BLUE = "\x1b[38;5;67m"
    MUTED_YELLOW = "\x1b[38;5;136m"
    MUTED_MAGENTA = "\x1b[38;5;132m"
    MUTED_CYAN = "\x1b[38;5;73m"

    # Text styles
    BOLD = "\x1b[1m"
    DIM = "\x1b[2m"
    ITALIC = "\x1b[3m"
    UNDERLINE = "\x1b[4m"
    BLINK = "\x1b[5m"
    REVERSE = "\x1b[7m"
    HIDDEN = "\x1b[8m"
    STRIKE = "\x1b[9m"

    # Reset
    RESET = "\x1b[0m"

    @classmethod
    def get(cls, name: str) -> str:
        """
        Looks up one or more ANSIColors code by readable name(s).
        The name argument can be a single color/style or several joined by '+'
        Matching is case-insensitive.

        Example:
            # Get single color
            red = ANSIColors.get('red')

            # Get bold blue color
            bold_blue = ANSIColors.get('blue+bold')
        """
        try:
            if '+' in name:
                return ''.join(cls[part.strip().upper()].value
                               for part in name.split('+'))
            return cls[name.strip().upper()].value
        except KeyError:
            raise ValueError(f"Color or style '{name}' not found")

    @classmethod
    def format(cls, message: str, level_color: Optional[str] = None) -> str:
        """
        Parses color tags from a message string and replaces with ANSI codes.
        Tags are replaced with the ANSI code corresponding to the tag name.
        A special `<level_color>` tag can also be used to colorize by log level.
        Unrecognized tags are ignored and left as-is in the message.

        Example:
            colorized = ANSIColors.format(
                "<green>Success:</green> File <blue>example.txt</blue> created"
                level_color='RED'
            )
            print(f"{colorized}")
        """
        result = message
        used_codes = []
        if level_color:
            try:
                color_code = cls.get(level_color)
                result = result.replace("<level_color>", color_code)
                used_codes.append(color_code)
            except ValueError:
                pass
        tags = re.findall(r'<([^>]+)>', result)
        for tag in dict.fromkeys(tags):
            if tag.lower() != "level_color":
                try:
                    code = cls.get(tag)
                    result = result.replace(f'<{tag}>', code)
                    used_codes.append(code)
                except ValueError:
                    pass
        if used_codes:
            result += cls.RESET.value
        return result


class LogFormatter(logging.Formatter):
    """
    Custom log message formatter with colorization and styling.

    A custom log record formatter that enables colorized output and dynamic
    control of log messages. Reads color tags from the logging format string
    and replaces them with the corresponding ANSI color code.

    Colorization can be enabled/disabled globally or selectively overridden.
    Optional mapping of log levels to colors allows dynamic styling by severity.

    Inherits from the standard logging.Formatter class.
    Automatically detects if the current env supports color output.

    Attributes:
        default_colors: Default mapping of log level to ANSI color code.

    Key methods:
        format: Overrides the superclass method to inject ANSI color codes.

    Example usage:
        console_format = "<<green>{asctime}</green> <level_color>{message}</level_color>"
        console_handler.setFormatter(LogFormatter(console_format))
    """

    default_colors = {
        logging.DEBUG: "GRAY + BOLD",
        logging.INFO: "MAGENTA + BOLD",
        logging.WARNING: "YELLOW + BOLD",
        logging.ERROR: "RED + BOLD",
        logging.CRITICAL: "MUTED_RED + BOLD"
    }

    def __init__(
            self,
            fmt: Optional[str] = None,
            datefmt: Optional[str] = None,
            style: Literal["%", "{", "$"] = '{',
            validate: bool = True,
            *,
            color_enabled: Optional[bool] = None,
            colors: Optional[Dict[int, str]] = None
    ):
        """
        Initializes a colored log message formatter.

        Args:
            fmt: The message format string, as per standard logging config.
                 Supports $, %, and {}-style string formatting + color tags.
            datefmt: The date/time format specifier as expected by strftime.
            style: Determines how the format string is parsed.
            validate: Fail fast if the format string is invalid.
            color_enabled: Override auto-color detect if true/false,
                           otherwise detects automatically.
            colors: Customize the mapping of log levels to colors.
                    Specified as int->str, e.g. {logging.INFO: 'white+bold'}

        Raises:
            ValueError: If `style` arg is not one of %, {, or $
        """
        if style not in ("%", "{", "$"):
            raise ValueError("Style must be one of: %, {, or $")
        super().__init__(fmt, datefmt, style, validate)
        self.color_enabled = detect_color_support() if color_enabled is None else color_enabled
        self.colors = {**self.default_colors, **(colors or {})}
        self._base_format = fmt

    def format(self, record: logging.LogRecord) -> str:
        """
        Converts LogRecord into a string with color formatting and styling.

        Override of the default Formatter.format method that injects ANSI color
        codes into the final message string based on color tags. Looks for both
        literal color tags like `<red>` as well as a special `<level_color>` tag
        that is replaced with the color for the LogRecord level.

        If color output is disabled, the tags are simply stripped out.

        Args:
            record: The LogRecord instance to format into a string

        Returns:
            str: The formatted, colorized log message string
        """
        # Save original values
        orig_msg = record.msg
        orig_levelname = record.levelname
        if self.color_enabled:
            # Get the level color before any formatting
            level_color = self.colors.get(record.levelno)
            # Create a temporary format string with the level color replaced
            if level_color:
                temp_fmt = self._base_format.replace('<level_color>', ANSIColors.get(level_color))
            else:
                temp_fmt = self._base_format
            # Set the temporary format
            self._style._fmt = temp_fmt
            # Apply standard formatting
            formatted_msg = super().format(record)
            # Apply remaining color formatting
            formatted_msg = ANSIColors.format(formatted_msg)
            # Restore the original format
            self._style._fmt = self._base_format
        else:
            # If colors are disabled, strip all color tags
            temp_fmt = re.sub(r'<[^>]+>', '', self._base_format)
            self._style._fmt = temp_fmt
            formatted_msg = super().format(record)
            self._style._fmt = self._base_format

        # Restore original values
        record.msg = orig_msg
        record.levelname = orig_levelname

        return formatted_msg


class AsyncLogger:
    """
    A flexible asynchronous logger with color support and file rotation.

    An advanced logger designed for asynchronous applications. Provides
    multi-level logging to console and/or files with ANSI color support,
    custom formatting, and automatic log file rotation.

    Logs are written asynchronously to avoid blocking application code.
    Provides robust protection against information leaks and log injection
    with automatic sanitization of log messages and extra data.

    Key features:
    - Async-compatible logging methods for all severity levels
    - Colored and styled console output with automatic terminal detection
    - Configurable log formats with custom fields
    - Automatic log file rotation based on size limits
    - Serializable JSON structured logging for easy parsing
    - Safe handling of exceptions during the logging process itself
    - Tracking of logger health metrics and failure statistics

    Attributes:
        logger (logging.Logger): The underlying standard library logger.
        metrics (LoggerMetrics): Tracks logger usage statistics and health.

    Key methods:
        log: Primary method to log a message at a specified severity level.
        debug: Log a message at DEBUG level severity.
        info: Log a message at INFO level severity.
        warning: Log a message at WARNING level severity.
        error: Log a message at ERROR level severity.
        critical: Log a message at CRITICAL level severity.
        shutdown: Cleanly shut down the logger, flushing all pending messages.

    Example usage:
        logger = AsyncLogger(name="ExampleLogger", log_dir="/logs")
        await logger.info("Informational message", extras={"context": "foo"})
        await logger.error("Something went wrong!", extras={"error": "FileNotFound"})
    """

    MAX_MESSAGE_LENGTH = 32768  # 32KB max message size
    MAX_KEY_LENGTH = 256  # Maximum length for extras keys
    MAX_VALUE_LENGTH = 1024  # Maximum length for extras values
    UNSAFE_KEY_PATTERN = re.compile(r'[^a-zA-Z0-9_.-]')

    default_console_format: str = (
        "[<red>{asctime}<reset>] [<level_color>{levelname:<8}<reset>] "
        "[<yellow>{funcName:^17}<reset>] <green>{name}<reset> {message}"
    )

    default_file_format: str = (
        "[{asctime}] [{levelname:<8}] [{funcName:^21}] {name}   {message}"
    )

    def __init__(self):
        """
        Directly initializing AsyncLoggers is disabled.

        Use `AsyncLogger.create()` instead. This allows async operations
        during initialization to be handled properly.
        """
        self._handler_lock = AsyncLock()
        self._extras_cache = {}
        self._cache_size = 1000
        self._failed_logs: Deque[FailedLogEntry] = deque(maxlen=100)
        self.logger = None
        self.metrics = LoggerMetrics()
        self._batch: List[logging.LogRecord] = []
        self._batch_size = 100
        self._flush_interval = 5.0
        self._last_flush = time.time()
        self._flush_task = None

    @classmethod
    async def create(
            cls,
            name: str,
            console_format: Optional[str] = None,
            file_format: Optional[str] = None,
            color_enabled: Optional[bool] = None,
            log_dir: Optional[Union[str, Path]] = None,
            max_bytes: int = 10_485_760,
            backup_count: int = 5,
            level: int = logging.DEBUG,
            colors: Optional[Dict[int, str]] = None,
    ) -> 'AsyncLogger':
        """
        Factory method that creates and initializes an AsyncLogger instance.
        Performs all async initialization steps required for the logger.

        Use this instead of directly initializing AsyncLogger instances.

        Args:
            name: A name for the logger, usually matching the application name
            console_format: Message format string for the console handler
            log_dir: Path to directory for storing rotated log files
            file_format: Message format string for the file handler
            color_enabled: Enable color output, auto-detected if not set
            max_bytes: Max size of a log file before it gets rotated
            backup_count: Number of rotated files to keep
            level: The minimum logging level (e.g. logging.INFO)
            colors: Customize colors assigned to each log level

        Returns:
            AsyncLogger: A fully configured AsyncLogger instance.

        Raises:
            LoggerConfigError: For any configuration errors.
        """
        if not isinstance(name, str) or not name.strip():
            raise LoggerConfigError("Logger name must be a non-empty string")
        if not isinstance(max_bytes, int) or max_bytes <= 0:
            raise LoggerConfigError("max_bytes must be a positive integer")
        if not isinstance(backup_count, int) or backup_count < 0:
            raise LoggerConfigError("backup_count must be a non-negative integer")
        instance = cls()
        try:
            instance.logger = logging.getLogger(name)
            instance.logger.setLevel(level)
            instance.logger.handlers = []
            console_handler = await instance._setup_console_handler(
                console_format, color_enabled, colors
            )
            instance.logger.addHandler(console_handler)
            if log_dir:
                file_handler = await instance._setup_file_handler(
                    log_dir, file_format, max_bytes, backup_count
                )
                instance.logger.addHandler(file_handler)
            instance._flush_task = asyncio.create_task(instance._periodic_flush())
            return instance
        except Exception as e:
            raise LoggerConfigError(f"Failed to initialize logger: {str(e)}")

    async def debug(self, msg: str, *args, extras: Optional[Dict[str, Any]] = None) -> None:
        """Log a message at the DEBUG severity level."""
        await self.log(logging.DEBUG, msg, *args, extras=extras)

    async def info(self, msg: str, *args, extras: Optional[Dict[str, Any]] = None) -> None:
        """Log a message at the INFO severity level."""
        await self.log(logging.INFO, msg, *args, extras=extras)

    async def warning(self, msg: str, *args, extras: Optional[Dict[str, Any]] = None) -> None:
        """Log a message at the WARNING severity level."""
        await self.log(logging.WARNING, msg, *args, extras=extras)

    async def error(self, msg: str, *args, extras: Optional[Dict[str, Any]] = None) -> None:
        """Log a message at the ERROR severity level."""
        await self.log(logging.ERROR, msg, *args, extras=extras)

    async def critical(self, msg: str, *args, extras: Optional[Dict[str, Any]] = None) -> None:
        """Log a message at the CRITICAL severity level."""
        await self.log(logging.CRITICAL, msg, *args, extras=extras)

    async def log(self, level: int, msg: str, *args, extras: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a message at the specified severity level.

        Logs a message to all configured handlers (e.g. console, file) after
        performing validation and sanitization on the message and extras.

        Automatically captures the caller's context (module, function, line).
        Records metrics on total messages logged and any errors.
        If an error occurs during the logging process itself, it is captured
        and an attempt is made to log an error before swallowing the exception.

        Args:
            level: The log severity level (e.g. logging.INFO)
            msg: The main message string to be logged
            extras: Optional supplementary data to include in the log message
        """
        frame = None
        caller_frame = None
        secured_msg = None
        try:
            # Validate message is not None
            if msg is None:
                # Explicitly record an error if the message is None
                self.metrics.record_error()
                # Create a failed log entry
                failed_entry = FailedLogEntry(
                    timestamp=datetime.datetime.now(),
                    level=level,
                    message='[empty message]',
                    error='Attempted to log None message'
                )
                self._failed_logs.append(failed_entry)
                msg = '[empty message]'
            if not isinstance(level, int):
                raise ValueError("Log level must be an integer")
            # Record metrics
            self.metrics.record_message()
            # Secure message immediately
            secured_msg = self._secure_message(msg)
            frame = inspect.currentframe()
            if frame and frame.f_back:
                caller_frame = frame.f_back.f_back
                context_name = 'main'
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        current_task = asyncio.current_task()
                        if current_task:
                            task_name = current_task.get_name()
                            if task_name.startswith('Task-') and current_task._coro.__name__ == 'process_task':  # NOQA
                                context_name = task_name
                except RuntimeError:
                    pass
                context_name = f"{context_name:^17}"
                formatted_msg = f"{secured_msg}{self._format_extras(extras)}"
                async with self._handler_lock:
                    old_func_name = self.logger.findCaller
                    try:
                        def get_caller_info(*args, **kwargs):
                            return (
                                caller_frame.f_code.co_filename,
                                caller_frame.f_lineno,
                                context_name,
                                None
                            )
                        self.logger.findCaller = get_caller_info
                        # Create the log record
                        record = self.logger.makeRecord(
                            self.logger.name, level,
                            caller_frame.f_code.co_filename,
                            caller_frame.f_lineno,
                            formatted_msg, args, None,
                            context_name
                        )
                        # Handle the record based on handler type
                        for handler in self.logger.handlers:
                            if isinstance(handler, RotatingFileHandler):
                                self._batch.append(record)
                                if len(self._batch) >= self._batch_size:
                                    await self._flush_batch()
                            else:
                                handler.handle(record)
                    finally:
                        self.logger.findCaller = old_func_name
            else:
                async with self._handler_lock:
                    formatted_msg = f"{secured_msg}{self._format_extras(extras)}"
                    self.logger.log(level, formatted_msg, *args)

        except Exception as e:
            self.metrics.record_error()
            final_secured_msg = secured_msg if secured_msg is not None else self._secure_message(msg)
            failed_entry = FailedLogEntry(
                timestamp=datetime.datetime.now(),
                level=level,
                message=final_secured_msg,
                error=str(e)
            )
            self._failed_logs.append(failed_entry)
            try:
                async with self._handler_lock:
                    self.logger.error(
                        f"Logging failed: {str(e)} | Attempted message: {final_secured_msg}"
                    )
            except Exception as inner_e:
                error_msg = (
                    f"Logging failed at {failed_entry.timestamp.isoformat()}: {str(e)} | "
                    f"Attempted message: {final_secured_msg}\n"
                    f"Secondary logging error: {str(inner_e)}"
                )
                print(error_msg, file=sys.stderr)

        finally:
            if frame:
                del frame
            if caller_frame:
                del caller_frame

    async def purge_logs(
            self,
            max_age_days: Optional[int] = 30,
            max_files: Optional[int] = 100,
            dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Purge old log files matching specified retention criteria.

        Scans the configured log directory and removes old log files. Files
        can be purged by age (older than max_age_days), count (keep newest
        max_files), or both.

        Specifying `None` for either max_age_days or max_files will ignore
        that constraint. If both are `None`, no logs will be purged.

        Dry run mode will perform all checks but not actually delete anything.

        Args:
            max_age_days: Purge logs older than this many days
            max_files: Retain at most this many of the newest log files
            dry_run: If True, only prints logs to remove, doesn't purge

        Returns:
            Dict[str, Any]: Stats on total logs, logs removed, removal errors

        Raises:
            LoggerConfigError: For invalid retention settings
        """
        if max_age_days is not None and max_age_days < 0:
            raise ValueError("max_age_days cannot be negative")
        if max_files is not None and max_files < 0:
            raise ValueError("max_files cannot be negative")
        stats = {
            "total_files": 0,
            "deleted_files": 0,
            "skipped_files": 0,
            "errors": []
        }
        log_dir = self._get_log_directory()
        if not log_dir:
            return stats
        try:
            log_files = await self._gather_log_files(log_dir)
            stats["total_files"] = len(log_files)
            current_date = datetime.datetime.now().date()
            for idx, (file_path, file_date) in enumerate(log_files):
                try:
                    should_delete = False
                    if max_age_days is not None and (current_date - file_date).days > max_age_days:
                        should_delete = True
                    if max_files is not None and idx >= max_files:
                        should_delete = True
                    if should_delete and not dry_run:
                        file_path.unlink()
                        stats["deleted_files"] += 1
                    elif should_delete:
                        stats["deleted_files"] += 1
                except Exception as e:
                    stats["errors"].append(f"Failed to process {file_path}: {str(e)}")
                    stats["skipped_files"] += 1
            return stats
        except Exception as e:
            stats["errors"].append(f"Error during log purge: {str(e)}")
            return stats

    def _format_extras(self, extras: Optional[Dict[str, Any]] = None) -> str:
        """
        Format a dict of extra log fields into a string, caches common keys.

        Converts a dict of user-provided extra keys and values into a string
        formatted for inclusion in a log line. Applies securing on values and
        keys. Caches the result based on a hash of the extras to speed up
        repeated logging of similar extras.

        Args:
            extras: The dict of extra log fields

        Returns:
            str: The formatted extras string or empty string if no extras
        """
        if not extras or not isinstance(extras, dict):
            return ""
        try:
            cache_key = tuple(sorted(
                (str(k), str(v)) for k, v in extras.items() if v is not None
            ))
            if not cache_key:
                return ""
            if cache_key in self._extras_cache:
                return self._extras_cache[cache_key]
            if len(self._extras_cache) >= self._cache_size:
                removal_count = max(1, self._cache_size // 4)
                oldest_keys = list(self._extras_cache.keys())[:removal_count]
                for key in oldest_keys:
                    self._extras_cache.pop(key)
            secured_extras = self._secure_extras(extras)
            if not secured_extras:
                return ""
            extras_str = ", ".join(
                f"{k}={v}" for k, v in secured_extras.items()
            )
            result = f" <bright_white>[{extras_str}]<reset>"
            self._extras_cache[cache_key] = result
            return result
        except Exception as e:
            return f" [extras_error: {str(e)}]"

    async def _setup_console_handler(
            self,
            console_format: Optional[str],
            color_enabled: Optional[bool],
            colors: Optional[Dict[int, str]]
    ) -> logging.Handler:
        """
        Configure the logger's console handler.
        Creates a handler for STDOUT using the color log formatter.

        Args:
            console_format: Message format string with color tags
            color_enabled: Color output override flag
            colors: Dict mapping log levels to color names like 'red+bold'

        Returns:
            logging.Handler: The configured StreamHandler for console output
        """
        async with self._handler_lock:
            try:
                console_handler = logging.StreamHandler(sys.stdout)
                formatter = LogFormatter(
                    console_format or self.default_console_format,
                    datefmt='%Y-%m-%d %H:%M:%S',
                    style='{',
                    color_enabled=color_enabled,
                    colors=colors
                )
                console_handler.setFormatter(formatter)
                return console_handler
            except Exception as e:
                raise LoggerConfigError(f"Failed to setup console handler: {str(e)}")

    async def _setup_file_handler(
            self,
            log_dir: Union[str, Path],
            file_format: Optional[str],
            max_bytes: int,
            backup_count: int
    ) -> logging.Handler:
        """
        Configure the logger's file rotation handler.
        Creates a RotatingFileHandler to write logs to disk with size limit.
        Ensures the log directory is created and writable before logging.

        Args:
            log_dir: Path to the directory for log files
            file_format: Message format string for log file entries
            max_bytes: Max size of log file before rotating, in bytes
            backup_count: Number of rotated log files to keep

        Returns:
            logging.Handler: The configured RotatingFileHandler
        """
        handler = None
        async with self._handler_lock:
            try:
                log_dir = await self._prepare_log_directory(Path(log_dir))
                log_file = await self._generate_log_filepath(log_dir)
                handler = RotatingFileHandler(
                    log_file,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding='utf-8',
                    delay=True
                )
                formatter = logging.Formatter(
                    file_format or self.default_file_format,
                    datefmt='%Y-%m-%d %H:%M:%S',
                    style='{'
                )
                handler.setFormatter(formatter)
                handler.acquire()
                handler.release()
                return handler
            except Exception as e:
                if handler:
                    handler.close()
                raise LoggerConfigError(f"Failed to setup file handler: {str(e)}") from e

    async def _prepare_log_directory(self, log_dir: Path) -> Path:
        """
        Ensure that the log directory exists and is writable.

        Args:
            log_dir: Path to the log directory

        Returns:
            Path: The validated log directory path

        Raises:
            LoggerConfigError: If the log directory cannot be created/accessed
        """
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            if not os.access(log_dir, os.W_OK):
                raise LoggerConfigError(f"Directory {log_dir} is not writable")
            return log_dir
        except Exception as e:
            raise LoggerConfigError(f"Failed to create log directory {log_dir}: {str(e)}") from e

    async def _generate_log_filepath(self, log_dir: Path) -> Path:
        """
        Generate a log file path incorporating current datetime.

        Args:
            log_dir: Path to the directory containing logs

        Returns:
            Path: The generated log file path

        Raises:
            LoggerConfigError: For errors generating the file path
        """
        try:
            log_file = log_dir / f"{datetime.datetime.now(datetime.UTC).date().isoformat()}.log"
            if log_file.exists():
                if not os.access(log_file, os.W_OK):
                    raise LoggerConfigError(f"Log file {log_file} is not writable")
                try:
                    log_file.chmod(0o644)
                except PermissionError as e:
                    await self.warning(
                        "Unable to set log file permissions",
                        extras={"file": str(log_file), "error": str(e)}
                    )
            return log_file
        except Exception as e:
            raise LoggerConfigError(f"Failed to generate log filepath: {str(e)}") from e

    def _get_log_directory(self) -> Optional[Path]:
        """
        Safely retrieve the current log directory path from logger handlers.

        Returns:
            Optional[Path]: The configured log directory if found, else None
        """
        for handler in self.logger.handlers:
            if isinstance(handler, RotatingFileHandler):
                return Path(handler.baseFilename).parent
        return None

    async def _gather_log_files(self, log_dir: Path) -> List[Tuple[Path, datetime.date]]:
        """
        Scan and validate all log files present in the given directory.

        Gathers all '.log' files from the directory and parses out their
        date from the filename for sorting and filtering. The log filenames
        are expected to be in the format 'YYYY-MM-DD.log'.

        Each log file is checked to ensure it is a valid file and the creation
        date can be parsed from the filename. Invalid log files are skipped.

        The log files are returned as a list of tuples containing the full
        file path and the parsed creation date, sorted descending by date.

        Args:
            log_dir: Path to the directory containing log files to scan

        Returns:
            List[Tuple[Path, datetime.date]]: List of tuples of the form
                (log file path, creation date) for each valid log file found,
                sorted with newest logs first.

        Raises:
            LoggerConfigError: If there is an error scanning the log directory,
                e.g. permission issues or unexpected filename formats
        """
        log_files = []
        for file in log_dir.glob("*.log"):
            try:
                # Verify file is valid and accessible
                if not file.is_file():
                    continue
                file_date = datetime.datetime.strptime(file.stem, "%Y-%m-%d").date()
                log_files.append((file, file_date))
            except ValueError:
                continue
        return sorted(log_files, key=lambda x: x[1], reverse=True)

    def _secure_message(self, message: Any) -> str:
        """
        Sanitize a message to guard against log injection and invalid chars.

        Converts the message to a string and strips out any characters that
        could enable log injection attacks or cause parsing issues. Sensitive
        characters like newlines and null bytes are safely escaped.

        If the message is too long, it is truncated to MAX_MESSAGE_LENGTH.
        If message conversion fails completely, a generic placeholder is used.

        Any exceptions during message cleanup will be caught and logged as errors.

        Args:
            message: The log message, can be any type

        Returns:
            str: The secured message string safe for logging
        """
        try:
            # Handle None case
            if message is None:
                return '[empty message]'
            # Handle dictionary case with improved formatting
            if isinstance(message, dict):
                try:
                    formatted_items = [f"{k}={v}" for k, v in message.items()]
                    message = f"[dict: {', '.join(formatted_items)}]"
                except Exception:
                    message = '[invalid dictionary]'
            # Handle other complex types
            elif isinstance(message, (list, tuple, set)):
                message = f"[{type(message).__name__}: {repr(message)}]"
            # Convert to string and normalize
            message = str(message)
            # Replace control characters
            message = message.replace('\0', ' ')
            message = message.replace('\n', '⏎').replace('\r', '⏎')
            # Normalize whitespace while preserving intentional spacing
            message = ' '.join(part for part in message.split(' ') if part)
            # Enforce length limit
            if len(message) > self.MAX_MESSAGE_LENGTH:
                truncated_length = self.MAX_MESSAGE_LENGTH - 15
                message = f"{message[:truncated_length]}[...TRUNCATED]"
            return message.strip()
        except Exception as e:
            return f"[Message conversion failed: {str(e)}]"

    def _secure_extras(self, extras: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, str]]:
        """
        Validate and sanitize a dict of extra attributes for structured logging.

        Recursively processes a dict of extra key-value pairs, converting
        values to strings and cleaning key names to ensure they are valid
        and don't contain any bespoke internal keys.

        If any value fails to convert to a string, it uses a placeholder.
        If the entire extras dict is invalid, an error is logged.

        Args:
            extras: Dict of extra key-value pairs to log

        Returns:
            Optional[Dict[str, Any]]: The validated and stringified extras
                                      dict or None if not provided
    """
        if not extras:
            return None
        try:
            secured = {}
            for key, value in extras.items():
                if value is not None:
                    safe_key = str(key)
                    safe_key = self.UNSAFE_KEY_PATTERN.sub('_', safe_key)
                    if safe_key.startswith('_'):
                        safe_key = 'x' + safe_key
                    if len(safe_key) > self.MAX_KEY_LENGTH:
                        safe_key = safe_key[:self.MAX_KEY_LENGTH - 3] + '...'
                    secured[safe_key] = self._secure_value(value)
            return secured
        except Exception as e:
            return {"error": f"Failed to process extras: {str(e)}"}

    def _secure_value(self, value: Any) -> str:
        """
        Safely convert a log record value to a string.

        Recursively converts dictionaries and iterables to strings, escaping
        any sensitive characters. A "log-safe string" is one where:
        - Null bytes ('\0') are replaced with spaces
        - Newline characters ('\n', '\r') are replaced with '⏎'
        - Strings longer than MAX_VALUE_LENGTH are truncated with ellipsis
        - Dictionaries and iterables are formatted with each item on one line

        Used to preprocess values in extra fields to ensure they log correctly.

        Args:
            value: The value to convert to a log-safe string

        Returns:
            str: The value converted to a string with proper escaping.
        """
        if value is None:
            return ''
        if isinstance(value, dict):
            try:
                formatted_items = [f"{k}={v}" for k, v in value.items()]
                return f"[dict: {', '.join(formatted_items)}]"
            except Exception:
                return '[invalid dictionary]'
        if isinstance(value, (list, tuple, set)):
            try:
                return f"[{type(value).__name__}: {', '.join(map(str, value))}]"
            except Exception:
                return f'[invalid {type(value).__name__}]'
        # Convert to string and apply standard security measures
        value_str = str(value)
        value_str = value_str.replace('\0', ' ')
        value_str = value_str.replace('\n', '⏎').replace('\r', '⏎')
        value_str = ' '.join(part for part in value_str.split(' ') if part)
        if len(value_str) > self.MAX_VALUE_LENGTH:
            value_str = f"{value_str[:self.MAX_VALUE_LENGTH - 3]}..."
        return value_str

    async def _periodic_flush(self) -> None:
        """Background task that periodically flushes batched log writes."""
        while True:
            try:
                await asyncio.sleep(self._flush_interval)
                if len(self._batch) > 0:  # Only flush if there are messages
                    await self._flush_batch()
            except Exception as e:
                self.metrics.record_error()
                if self.logger:  # Add this check
                    self.logger.error(f"Flush error: {str(e)}")
                else:
                    print(f"Flush error: {str(e)}", file=sys.stderr)

    async def _flush_batch(self) -> None:
        """Immediately write any buffered log messages to disk."""
        async with self._handler_lock:
            if self._batch:
                try:
                    for handler in self.logger.handlers:
                        if isinstance(handler, RotatingFileHandler):
                            for record in self._batch:
                                handler.emit(record)
                    self._batch.clear()
                    self._last_flush = time.time()
                except Exception as e:
                    self.metrics.record_error()
                    if self.logger:
                        self.logger.error(f"Batch flush failed: {str(e)}")

    async def get_failed_logs(self) -> List[FailedLogEntry]:
        """Retrieve all failed log messages that could not be logged."""
        return list(self._failed_logs)

    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get a snapshot of internal logger state and metrics.

        Returns a dictionary with the following metrics:

        - total_messages: Cumulative count of all messages processed. A high
          value indicates the logger is processing a large volume of messages.

        - error_count: Number of messages that encountered an error during
          processing. A high count relative to total_messages may indicate
          issues with log processing that require investigation.

        - last_error_time: Timestamp of the most recent error. Useful for
          identifying when the last error occurred and tracking error frequency.

        - batch_size: Number of messages currently queued for writing to disk.
          A high value may indicate issues with the file writing process.

        - time_since_flush: Time in seconds since the last batch of messages
          was flushed to disk. A high value may suggest issues preventing
          writes or a need to tune the flush interval.

        - failed_logs_count: Number of log messages that failed processing
          and were captured as Failed Log Entries for later review.

        - extras_cache_size: Number of keys in the extras cache. Can be used
          to monitor memory usage and identify any unexpected growth over time.

        Returns:
            Dict[str, Any]: Logger state and metrics
        """
        return {
            "total_messages": self.metrics.total_messages,
            "error_count": self.metrics.error_count,
            "last_error_time": self.metrics.last_error_time,
            "batch_size": len(self._batch),
            "time_since_flush": time.time() - self._last_flush,
            "failed_logs_count": len(self._failed_logs),
            "extras_cache_size": len(self._extras_cache)
        }

    async def shutdown(self) -> None:
        """
        Cleanly shut down the logger.

        Flushes any pending writes, cancels periodic flush task,
        closes all log handlers, and releases locks.

        Should be called before application exit.
        """
        try:
            # Final flush of any remaining messages
            await self._flush_batch()
            if self._flush_task:
                self._flush_task.cancel()
            async with self._handler_lock:
                if self.logger and self.logger.handlers:
                    handlers_copy = self.logger.handlers[:]
                    for handler in handlers_copy:
                        try:
                            handler.close()
                            self.logger.removeHandler(handler)
                        except Exception as e:
                            print(f"Error closing handler: {str(e)}", file=sys.stderr)
                    self.logger = None
        except Exception as e:
            print(f"Error during logger shutdown: {str(e)}", file=sys.stderr)


async def process_task(logger: AsyncLogger, task_id: int):
    """Mock function demonstrating async logger in an async context."""
    await logger.info(
        f"Processing task {task_id}",
        extras={"task_number": task_id, "status": "running"}
    )


async def example():
    """
    Comprehensive example demonstrating AsyncLogger usage in an application.

    The example covers:
    - Creating an AsyncLogger instance with custom configuration
    - Logging messages at various severity levels (debug, info, warning,etc.)
    - Passing extra context information with log messages
    - Processing log messages in an asynchronous context using TaskGroup
    - Error handling and capturing failed log messages
    - Testing message and extras sanitization and truncation
    - Logger shutdown and cleanup

    This example provides a practical reference for integrating the
    AsyncLogger into a real-world asynchronous application, illustrating
    key features, best practices, and potential pitfalls to be aware of.
    """
    logger = await AsyncLogger.create(
        name="TestApplication",
        log_dir="logs",
        color_enabled=True,
        level=logging.DEBUG,
        colors={
            logging.INFO: "BLUE + BOLD"
        }
    )
    try:
        await logger.info("Application initialization started", extras={"version": "2.0.0"})
        await logger.debug("Configuration loaded successfully")
        async with asyncio.TaskGroup() as tg:
            for i in range(3):
                tg.create_task(
                    process_task(logger, i),
                    name=f"Task-{i}"
                )
        await logger.warning(
            "Resource usage warning",
            extras={"cpu_usage": "85%", "memory_usage": "75%"}
        )
        await logger.error(
            "Database connection failed",
            extras={"attempt": 1, "host": "localhost", "port": 5432}
        )
        await logger.critical(
            "System shutdown initiated",
            extras={"reason": "maintenance", "scheduled": True}
        )
        # Test error handling by forcing different types of errors
        await logger.log(logging.INFO, None)  # This should trigger the error handling
        await logger.log(logging.INFO, {"invalid": "message"})  # Another error case
        # Test message security
        await logger.info("Normal message")
        await logger.info("Message with newlines\nand\rcarriage returns")
        await logger.info("Message with null bytes\0and other control characters")
        # Test extras security
        await logger.info(
            "Testing extras security",
            extras={
                "normal_key": "normal value",
                "unsafe!key": "value with newlines\n",
                "_system": "sensitive data",
                "nested": {"key": "value"},
                "long" * 100: "long" * 1000
            }
        )

    except Exception as e:
        print(f"Main function error: {str(e)}")
    finally:
        await logger.shutdown()


if __name__ == "__main__":
    asyncio.run(example())
