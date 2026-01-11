"""
Personal Assistant: Manual Briefing Trigger Command

Manually generate and deliver briefings on demand (for testing and manual use).

Usage:
    python -m commands.pa.briefing morning
    python -m commands.pa.briefing evening --dry-run
    python -m commands.pa.briefing morning --config /path/to/config.json
    python -m commands.pa.briefing evening --energy-level 7

Model: Template-based (no LLM by default)
"""

import argparse
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.briefing_engine import BriefingEngine


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration file.

    Args:
        config_path: Optional path to config file. Defaults to config/briefing_schedule.json

    Returns:
        Configuration dictionary
    """
    if config_path is None:
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "briefing_schedule.json"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = json.load(f)

    return config


def save_to_file(briefing: str, briefing_type: str, output_dir: Optional[str] = None) -> str:
    """
    Save briefing to file.

    Args:
        briefing: The briefing content
        briefing_type: Type of briefing (morning/evening)
        output_dir: Optional output directory. Defaults to History/DailyBriefings

    Returns:
        Path to saved file
    """
    if output_dir is None:
        project_root = Path(__file__).parent.parent.parent
        output_dir = project_root / "History" / "DailyBriefings"
    else:
        output_dir = Path(output_dir)

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now()
    date_str = timestamp.strftime('%Y-%m-%d')
    time_str = timestamp.strftime('%H%M')
    filename = f"{date_str}_{briefing_type}_briefing_{time_str}.md"

    file_path = output_dir / filename

    # Write file
    with open(file_path, 'w') as f:
        f.write(f"# {briefing_type.capitalize()} Briefing - {timestamp.strftime('%B %d, %Y')}\n\n")
        f.write(f"*Generated at {timestamp.strftime('%I:%M %p')}*\n\n")
        f.write(briefing)

    return str(file_path)


def generate_briefing(
    briefing_type: str,
    config: Dict[str, Any],
    energy_level: Optional[int] = None,
    dry_run: bool = False,
    logger: Optional[logging.Logger] = None
) -> int:
    """
    Generate and deliver a briefing.

    Args:
        briefing_type: Type of briefing (morning/evening)
        config: Configuration dictionary
        energy_level: Optional energy level (1-10)
        dry_run: If True, print without saving
        logger: Logger instance

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # Validate briefing type
    if briefing_type not in ['morning', 'evening']:
        logger.error(f"Invalid briefing type: {briefing_type}. Must be 'morning' or 'evening'.")
        return 1

    # Get project root
    project_root = Path(__file__).parent.parent.parent

    # Get paths from config
    state_dir = project_root / config.get('advanced', {}).get('state_dir', 'State')
    templates_dir = project_root / config.get('advanced', {}).get('templates_dir', 'Templates')

    # Initialize BriefingEngine
    try:
        engine = BriefingEngine(
            state_dir=str(state_dir),
            templates_dir=str(templates_dir)
        )
    except Exception as e:
        logger.error(f"Failed to initialize BriefingEngine: {e}")
        return 1

    # Print header
    today = datetime.now().strftime("%A, %B %d, %Y")
    emoji = "☀️" if briefing_type == "morning" else "🌙"

    print(f"\n{emoji}  Generating {briefing_type} briefing for {today}...")

    if dry_run:
        print("🔍 DRY RUN MODE - Output will not be saved\n")

    if energy_level is not None:
        print(f"⚡ Energy level: {energy_level}/10\n")

    print("-" * 60)

    # Gather context
    try:
        context = engine.gather_context()
        logger.debug(f"Context gathered: {len(context.get('commitments', []))} commitments, "
                    f"{len(context.get('this_week', {}).get('tasks', []))} tasks")
    except Exception as e:
        logger.error(f"Failed to gather context: {e}")
        print(f"\n❌ Error gathering context: {e}")
        return 1

    # Render briefing
    try:
        briefing = engine.render_briefing(
            briefing_type=briefing_type,
            context=context,
            energy_level=energy_level
        )
    except Exception as e:
        logger.error(f"Failed to render briefing: {e}")
        print(f"\n❌ Error rendering briefing: {e}")
        return 1

    # Print briefing
    print(briefing)
    print("\n" + "-" * 60)

    # Save to file if not dry run
    if not dry_run:
        try:
            output_dir = config.get('delivery', {}).get('file', {}).get('output_dir')
            if output_dir:
                output_dir = project_root / output_dir
            else:
                output_dir = None

            file_path = save_to_file(briefing, briefing_type, output_dir)
            print(f"💾 Saved to: {file_path}")
            logger.info(f"Briefing saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save briefing: {e}")
            print(f"\n⚠️  Warning: Failed to save briefing to file: {e}")
            # Don't return error code since briefing was generated successfully
    else:
        print("📋 Dry run complete - no file saved")

    print(f"\n✅ {briefing_type.capitalize()} briefing generated successfully!\n")
    return 0


def main():
    """Main entry point for the command."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Manually generate and deliver briefings on demand',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m commands.pa.briefing morning
  python -m commands.pa.briefing evening --dry-run
  python -m commands.pa.briefing morning --config /path/to/config.json
  python -m commands.pa.briefing evening --energy-level 7
  python -m commands.pa.briefing morning --dry-run --verbose
        """
    )

    parser.add_argument(
        'type',
        choices=['morning', 'evening'],
        help='Type of briefing to generate'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print briefing without saving to file'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Path to custom config file (default: config/briefing_schedule.json)'
    )

    parser.add_argument(
        '--energy-level',
        type=int,
        choices=range(1, 11),
        metavar='1-10',
        help='Your current energy level (1=low, 10=high) - affects task recommendations'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.verbose)

    # Load configuration
    try:
        config = load_config(args.config)
        logger.debug(f"Loaded config from {args.config or 'config/briefing_schedule.json'}")
    except FileNotFoundError as e:
        logger.error(str(e))
        print(f"\n❌ Error: {e}")
        print("Please ensure the config file exists or provide a valid --config path.\n")
        return 1
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        print(f"\n❌ Error: Invalid JSON in config file: {e}\n")
        return 1
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        print(f"\n❌ Error loading config: {e}\n")
        return 1

    # Generate briefing
    exit_code = generate_briefing(
        briefing_type=args.type,
        config=config,
        energy_level=args.energy_level,
        dry_run=args.dry_run,
        logger=logger
    )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
