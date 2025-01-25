#!/usr/bin/env python3
"""
AsyncLogger Color Formatting Demonstration

An interactive script showcasing the color and styling capabilities
of the AsyncLogger framework.
"""

import asyncio
import logging
import sys
from typing import Dict, List, Optional


class ColorFormattingDemo:
    """
    Interactive demonstration of AsyncLogger's color formatting capabilities.
    """

    # Comprehensive color and style categories
    COLORS = {
        'basic': ['BLACK', 'RED', 'GREEN', 'YELLOW', 'BLUE', 'MAGENTA', 'CYAN', 'WHITE', 'GRAY'],
        'dark': ['DARK_RED', 'DARK_GREEN', 'DARK_YELLOW', 'DARK_BLUE', 'DARK_MAGENTA', 'DARK_CYAN', 'DARK_GRAY'],
        'bright': ['BRIGHT_RED', 'BRIGHT_GREEN', 'BRIGHT_YELLOW', 'BRIGHT_BLUE', 'BRIGHT_MAGENTA', 'BRIGHT_CYAN',
                   'BRIGHT_WHITE'],
        'muted': ['MUTED_RED', 'MUTED_GREEN', 'MUTED_BLUE', 'MUTED_YELLOW', 'MUTED_MAGENTA', 'MUTED_CYAN'],
        'styles': ['BOLD', 'DIM', 'ITALIC', 'UNDERLINE', 'BLINK', 'REVERSE', 'HIDDEN', 'STRIKE']
    }

    def __init__(self):
        """Initialize the color formatting demonstration."""
        self.logger = None

    async def create_logger(self):
        """
        Create an AsyncLogger instance for the demonstration.

        Returns:
            AsyncLogger: Configured logger instance
        """
        try:
            from asyncLogger import AsyncLogger

            self.logger = await AsyncLogger.create(
                name="ColorDemo",
                color_enabled=True,
                level=logging.INFO
            )
            return self.logger
        except ImportError:
            print("AsyncLogger is not installed. Please install it first.")
            return None

    def display_header(self):
        """Display the demo introduction."""
        print("\n" + "=" * 50)
        print("AsyncLogger Color Formatting Demo".center(50))
        print("=" * 50)
        print("\nExplore the rich color and styling capabilities of AsyncLogger.")
        print("Navigate through different color categories and styles.\n")

    def display_menu(self):
        """
        Display an interactive menu for color and style selection.

        Returns:
            Tuple containing selected category, color/style, and combined style
        """
        self.display_header()

        print("Select a color category:")
        for i, category in enumerate(self.COLORS.keys(), 1):
            print(f"{i}. {category.capitalize()} Colors")

        try:
            category_choice = int(input("\nEnter category number: "))
            category = list(self.COLORS.keys())[category_choice - 1]
        except (ValueError, IndexError):
            print("Invalid selection. Defaulting to basic colors.")
            category = 'basic'

        print(f"\nAvailable {category.capitalize()} Colors/Styles:")
        for i, color in enumerate(self.COLORS[category], 1):
            print(f"{i}. {color}")

        try:
            color_choice = int(input("\nSelect a color/style number: "))
            selected_color = self.COLORS[category][color_choice - 1]
        except (ValueError, IndexError):
            print("Invalid selection. Using default.")
            selected_color = self.COLORS[category][0]

        # Handle style combinations for 'styles' category
        combined_style = ''
        if category == 'styles':
            combine_choice = input("Combine multiple styles? (y/n): ").lower()
            if combine_choice == 'y':
                print("\nAvailable styles:")
                for i, style in enumerate(self.COLORS['styles'], 1):
                    print(f"{i}. {style}")

                style_indices = input("Enter style numbers (comma-separated): ")
                try:
                    selected_styles = [self.COLORS['styles'][int(s.strip()) - 1] for s in style_indices.split(',')]
                    combined_style = '+'.join(selected_styles)
                except (ValueError, IndexError):
                    print("Invalid style selection. Using single style.")

        return category, selected_color, combined_style

    async def demonstrate_formatting(self, category: str, color: str, style: str = ''):
        """
        Demonstrate log message formatting with selected colors and styles.

        Args:
            category (str): The color category selected
            color (str): The specific color or style to apply
            style (str, optional): Additional styles to combine
        """
        if not self.logger:
            print("Logger not initialized. Please run the demo first.")
            return

        # Generate log message with color tags
        full_tag = f"{style + '+' if style else ''}{color}"
        message = f"AsyncLogger Color Demo: {category.capitalize()} {color}"

        print("\n=== Formatting Demonstration ===")
        print(f"Selected Category: {category}")
        print(f"Selected Color/Style: {full_tag}")
        print(f"Log Message Format: <{full_tag}>{message}</{color}>{f'</{style}>' if style else ''}")

        # Log the message with selected formatting
        try:
            await self.logger.info(
                f"<{full_tag}>{message}</{color}>{f'</{style}>' if style else ''}",
                extras={"demo_category": category}
            )
            print("\nLog message sent successfully!")
        except Exception as e:
            print(f"Error logging message: {e}")

    async def run_demo(self):
        """
        Main method to run the interactive color formatting demonstration.
        """
        # Initialize logger
        await self.create_logger()

        if not self.logger:
            return

        while True:
            # Display interactive menu and get user selections
            category, color, style = self.display_menu()

            # Demonstrate selected formatting
            await self.demonstrate_formatting(category, color, style)

            # Ask if user wants to continue
            continue_demo = input("\nContinue exploring? (y/n): ").lower()
            if continue_demo != 'y':
                break

        # Shutdown logger
        await self.logger.shutdown()
        print("\nColor Formatting Demo Completed. Thank you!")


async def main():
    """
    Entry point for the AsyncLogger Color Formatting Demo.
    """
    demo = ColorFormattingDemo()
    await demo.run_demo()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo interrupted. Exiting gracefully.")
        sys.exit(0)
