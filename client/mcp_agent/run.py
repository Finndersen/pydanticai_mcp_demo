from pathlib import Path
import readline

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models import Model
from rich.console import Console
from rich.prompt import Prompt

from mcp_agent.agent import get_agent
from mcp_agent.deps import AgentDeps
from mcp_agent.tools import get_tools

EXIT_COMMANDS = ["/quit", "/exit", "/q"]


async def run(model: Model, working_directory: Path):
    """Initialise services and run agent conversation loop."""
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="npx",  # Executable
        args=[
            "tsx",
            "server/index.ts",
            str(working_directory),
        ],
    )

    console = Console()

    deps = AgentDeps(console=console, current_working_directory=working_directory)

    # Print welcome message
    console.print("[cyan]Welcome to MCP Demo CLI! Type [bold]/quit[/bold] to exit.\n[/cyan]")
    console.print(f"Starting MCP server with working directory: {working_directory}")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            
            tools = await get_tools(session)

            agent = await get_agent(model=model, deps=deps, tools=tools)

            message_history: list[ModelMessage] = []
            while True:
                prompt = Prompt.ask("[cyan]>[/cyan] ").strip()

                if not prompt:
                    continue

                # Handle special commands
                if prompt.lower() in EXIT_COMMANDS:
                    console.print("[yellow]Exiting...[/yellow]")
                    break

                # Process normal input through the agent
                result = await agent.run(prompt, deps=deps, message_history=message_history)
                response = result.data

                console.print(f"[bold green]Agent:[/bold green] {response}")
                message_history = result.all_messages()
