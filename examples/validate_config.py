#!/usr/bin/env python
"""
Example script for validating crawl4ai_llm configuration.

This script loads and validates configuration from a YAML or JSON file,
displaying any validation errors or warnings.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import ValidationError

from crawl4ai_llm.config import AppConfig


def load_config_file(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML or JSON file.

    Args:
        config_path: Path to configuration file

    Returns:
        Dict containing configuration values

    Raises:
        ValueError: If file format is not supported or parsing fails
    """
    file_path = Path(config_path)

    if not file_path.exists():
        raise ValueError(f"Configuration file not found: {config_path}")

    if file_path.suffix.lower() in [".yaml", ".yml"]:
        try:
            with open(file_path, "r") as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML configuration: {str(e)}")
    elif file_path.suffix.lower() == ".json":
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON configuration: {str(e)}")
    else:
        raise ValueError(f"Unsupported configuration file format: {file_path.suffix}")


def validate_config(config_data: Dict[str, Any]) -> Optional[AppConfig]:
    """
    Validate configuration data against Pydantic models.

    Args:
        config_data: Dictionary of configuration data

    Returns:
        Validated AppConfig instance or None if validation fails
    """
    try:
        app_config = AppConfig.parse_obj(config_data)
        return app_config
    except ValidationError as e:
        print("\n❌ Configuration validation failed:\n")
        for error in e.errors():
            location = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            print(f"  - Error in '{location}': {message}")
        return None


def display_config_summary(config: AppConfig) -> None:
    """
    Display a summary of the validated configuration.

    Args:
        config: Validated AppConfig instance
    """
    print("\n✅ Configuration validated successfully\n")

    print("🔍 Crawler Configuration:")
    print(f"  - User Agent: {config.crawler.user_agent}")
    print(f"  - Timeout: {config.crawler.timeout} seconds")
    print(f"  - Max Retries: {config.crawler.max_retries}")
    print(
        f"  - Rate Limit: {config.crawler.rate_limit.requests} requests per {config.crawler.rate_limit.period} seconds"
    )

    print("\n💾 Storage Configuration:")
    print(f"  - Type: {config.storage.type}")
    print(f"  - Path: {config.storage.path}")
    print(f"  - Use UUID: {config.storage.use_uuid}")

    print("\n🤖 LLM Configuration:")
    print(f"  - Provider: {config.llm.provider}")
    print(f"  - Model: {config.llm.model}")
    if config.llm.api_key:
        print(
            f"  - API Key: {'*' * 8}{config.llm.api_key[-4:] if len(config.llm.api_key) > 4 else ''}"
        )
    print(f"  - Temperature: {config.llm.temperature}")
    print(f"  - Cache Enabled: {config.llm.use_cache}")
    if config.llm.cache_dir:
        print(f"  - Cache Directory: {config.llm.cache_dir}")

    if config.extras:
        print("\n⚙️ Extra Configuration:")
        for key, value in config.extras.items():
            print(f"  - {key}: {value}")


def create_example_config(output_path: str, format_type: str = "yaml") -> None:
    """
    Create an example configuration file.

    Args:
        output_path: Path to save example configuration
        format_type: Format type (yaml or json)
    """
    example_config = {
        "crawler": {
            "user_agent": "crawl4ai/1.0 (+https://example.com/bot)",
            "timeout": 30,
            "max_retries": 3,
            "rate_limit": {"requests": 1, "period": 2},
        },
        "storage": {"type": "json", "path": "./data", "use_uuid": True},
        "llm": {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": "your_api_key_here",
            "temperature": 0.1,
            "use_cache": True,
            "cache_dir": "./llm_cache",
        },
        "extras": {
            "debug": False,
            "extraction_strategy": "auto",
            "save_raw_html": True,
        },
    }

    output_file = Path(output_path)

    # Create directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Determine format from file extension if not specified
    if format_type == "auto":
        if output_file.suffix.lower() in [".yaml", ".yml"]:
            format_type = "yaml"
        elif output_file.suffix.lower() == ".json":
            format_type = "json"
        else:
            format_type = "yaml"  # Default to YAML

    # Write configuration file
    if format_type == "yaml":
        with open(output_file, "w") as f:
            yaml.dump(example_config, f, default_flow_style=False, sort_keys=False)
    else:
        with open(output_file, "w") as f:
            json.dump(example_config, f, indent=2)

    print(f"Example configuration created at: {output_file}")


def main():
    """Parse command line arguments and validate configuration."""
    parser = argparse.ArgumentParser(
        description="Validate crawl4ai_llm configuration file"
    )

    # Create subparsers for different actions
    subparsers = parser.add_subparsers(dest="action", help="Action to perform")

    # Validate config subparser
    validate_parser = subparsers.add_parser(
        "validate", help="Validate configuration file"
    )
    validate_parser.add_argument(
        "config_file", help="Path to configuration file (YAML or JSON)"
    )

    # Create example config subparser
    example_parser = subparsers.add_parser(
        "create-example", help="Create example configuration file"
    )
    example_parser.add_argument(
        "output_file", help="Path to save example configuration file"
    )
    example_parser.add_argument(
        "--format",
        choices=["yaml", "json", "auto"],
        default="auto",
        help="Output format (default: auto-detect from file extension)",
    )

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(1)

    if args.action == "validate":
        try:
            config_data = load_config_file(args.config_file)
            config = validate_config(config_data)
            if config:
                display_config_summary(config)
                sys.exit(0)
            else:
                sys.exit(1)
        except ValueError as e:
            print(f"Error: {str(e)}")
            sys.exit(1)
    elif args.action == "create-example":
        create_example_config(args.output_file, args.format)
        sys.exit(0)


if __name__ == "__main__":
    main()
