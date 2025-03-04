from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models import Model
from rich.console import Console
from rich.prompt import Prompt

from mcp_demo.agent import get_agent
from mcp_demo.deps import AgentDeps

EXIT_COMMANDS = ["/quit", "/exit", "/q"]


async def run(model: Model, working_directory: Path):
    """Initialise services and run agent conversation loop."""
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="npx",  # Executable
        args=[
            "-y",
            "@modelcontextprotocol/server-filesystem",
            str(working_directory),
        ],  # Optional command line arguments
        env=None,  # Optional environment variables
    )

    console = Console()

    deps = AgentDeps(console=console, current_working_directory=working_directory)

    # Print welcome message
    console.print("[bold cyan]Welcome to MCP Demo CLI[/bold cyan]")
    console.print("Type [cyan]/help[/cyan] for available commands or [cyan]/quit[/cyan] to exit.\n")

    console.print(f"Starting MCP server with working directory: {working_directory}")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            agent = await get_agent(model=model, deps=deps, session=session)

            message_history: list[ModelMessage] = []
            while True:
                # Use prompt_toolkit for input with arrow key support
                try:
                    prompt = Prompt.ask("[cyan]>[/cyan] ")
                    prompt = prompt.strip()
                except KeyboardInterrupt:
                    console.print("\n[yellow]Interrupted by user. Exiting...[/yellow]")
                    break
                except EOFError:
                    console.print("\n[yellow]EOF received. Exiting...[/yellow]")
                    break

                if not prompt:
                    continue

                # Handle special commands
                if prompt.lower() in EXIT_COMMANDS:
                    console.print("[yellow]Exiting...[/yellow]")
                    break
                elif prompt.lower() == "/clear":
                    console.clear()
                    continue

                # Process normal input through the agent
                result = await agent.run(prompt, deps=deps, message_history=message_history)
                response = result.data

                console.print(f"[bold green]Agent:[/bold green] {response.message}")

                # Exit if LLM indicates conversation is over
                if response.end_conversation:
                    console.print("[yellow]Agent indicated the conversation is complete. Exiting...[/yellow]")
                    break

                message_history = result.all_messages()

            console.print("[bold cyan]Thank you for using MCP Demo CLI![/bold cyan]")
