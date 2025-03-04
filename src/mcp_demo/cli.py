#!/usr/bin/env python3

import argparse
import asyncio
import os
from pathlib import Path

import logfire
from rich.console import Console

from mcp_demo.llm import build_model_from_name_and_api_key
from mcp_demo.run import run


def main():
    """Command-line interface for mcp_demo."""
    parser = argparse.ArgumentParser(description="Run an AI development assistant with a specified LLM model.")

    parser.add_argument(
        "working_directory", type=str, help="Working directory to use for the assistant", default=os.getcwd(), nargs="?"
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM model name to use, e.g. gpt-4o, claude-3-7-sonnet-latest, gemini-2.0-flash. "
        "Can infer from environment variable API keys if not provided.",
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for the LLM service. If not provided, will try to use environment variable.",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode, which will print debug messages to the console.",
    )

    args = parser.parse_args()

    logfire.configure(send_to_logfire="if-token-present", console=None if args.debug else False)

    # Build the model from name and API key
    model = build_model_from_name_and_api_key(args.model, args.api_key)
    if model is None:
        console = Console()
        console.print("[bold red]Error:[/] Could not build a model. Please provide a valid model name and/or API key.")
        return 1

    # Run the assistant
    asyncio.run(run(model=model, working_directory=Path(args.working_directory)))

    return 0


if __name__ == "__main__":
    exit(main())
