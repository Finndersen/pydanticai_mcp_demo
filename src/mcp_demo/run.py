from mcp.types import CallToolResult
from pydantic_ai.models import Model
from pydantic_ai.messages import ModelMessage
from pydantic_ai.tools import Tool
from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import WordCompleter

from mcp_demo.agent import get_agent
from mcp_demo.deps import AgentDeps
from mcp import ClientSession, StdioServerParameters, Tool as MCPTool
from mcp.client.stdio import stdio_client


EXIT_COMMANDS = ["/quit", "/exit", "/q"]
HELP_COMMANDS = ["/help", "/h", "/?"]

# Define some common commands for auto-completion
CLI_COMMANDS = EXIT_COMMANDS + HELP_COMMANDS + [
    "/clear",
    "/history",
    "Hello",
    "What can you do?",
    "Help me with",
    "Explain",
    "Create",
    "Fix",
    "Optimize",
    "Debug",
]

# Define a style for the prompt
PROMPT_STYLE = Style.from_dict({
    'prompt': 'ansicyan bold',
    'user-input': 'ansigreen',
})


def print_help(console):
    """Print help information about available commands."""
    console.print("\n[bold cyan]Available Commands:[/bold cyan]")
    console.print("  [cyan]/help[/cyan], [cyan]/h[/cyan], [cyan]/?[/cyan] - Show this help message")
    console.print("  [cyan]/quit[/cyan], [cyan]/exit[/cyan], [cyan]/q[/cyan] - Exit the application")
    console.print("  [cyan]/clear[/cyan] - Clear the screen")
    console.print("  [cyan]/history[/cyan] - Show command history")
    console.print("\n[bold cyan]Tips:[/bold cyan]")
    console.print("  • Use arrow keys (↑/↓) to navigate through command history")
    console.print("  • Tab key provides command completion")
    console.print("  • Ctrl+C or Ctrl+D to exit\n")


async def run(model: Model, working_directory: str):
    """Initialise services and run agent conversation loop."""
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="npx", # Executable
        args=["-y", "@modelcontextprotocol/server-filesystem", working_directory], # Optional command line arguments
        env=None # Optional environment variables
    )
    
    deps = AgentDeps(console=Console(), current_working_directory=working_directory)
    console = deps.console
    
    # Create a completer for command suggestions
    command_completer = WordCompleter(CLI_COMMANDS, ignore_case=True)
    
    # Create a prompt session with history support
    prompt_history = InMemoryHistory()
    session_prompt = PromptSession(
        history=prompt_history,
        auto_suggest=AutoSuggestFromHistory(),
        completer=command_completer,
        style=PROMPT_STYLE,
        complete_in_thread=True,
    )
    
    # Print welcome message
    console.print("[bold cyan]Welcome to MCP Demo CLI[/bold cyan]")
    console.print("Type [cyan]/help[/cyan] for available commands or [cyan]/quit[/cyan] to exit.\n")
                
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            agent = await get_agent(model=model, deps=deps, session=session)

            message_history: list[ModelMessage] = []
            while True:
                # Use prompt_toolkit for input with arrow key support
                try:
                    prompt = await session_prompt.prompt_async(
                        HTML("<prompt>You:</prompt> "),
                        style=PROMPT_STYLE
                    )
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
                elif prompt.lower() in HELP_COMMANDS:
                    print_help(console)
                    continue
                elif prompt.lower() == "/clear":
                    console.clear()
                    continue
                elif prompt.lower() == "/history":
                    console.print("\n[bold cyan]Command History:[/bold cyan]")
                    for i, cmd in enumerate(list(prompt_history.get_strings())[-10:], 1):
                        console.print(f"  {i}. {cmd}")
                    console.print()
                    continue

                # Process normal input through the agent
                try:
                    result = await agent.run(prompt, deps=deps, message_history=message_history)
                    response = result.data
                    
                    console.print(f"[bold green]Agent:[/bold green] {response.message}")

                    # Exit if LLM indicates conversation is over
                    if response.end_conversation:
                        console.print("[yellow]Agent indicated the conversation is complete. Exiting...[/yellow]")
                        break
                except Exception as e:
                    console.print(f"[bold red]Error:[/bold red] {str(e)}")
                    
            console.print("[bold cyan]Thank you for using MCP Demo CLI![/bold cyan]")
        
