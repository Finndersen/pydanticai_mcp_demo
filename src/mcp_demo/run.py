from mcp.types import CallToolResult
from pydantic_ai.models import Model
from pydantic_ai.messages import ModelMessage
from pydantic_ai.tools import Tool
from rich.console import Console
from rich.prompt import Prompt

from mcp_demo.agent import get_agent
from mcp_demo.deps import AgentDeps
from mcp import ClientSession, StdioServerParameters, Tool as MCPTool
from mcp.client.stdio import stdio_client


EXIT_COMMANDS = ["/quit", "/exit", "/q"]


async def run(model: Model, working_directory: str):
    """Initialise services and run agent conversation loop."""
        # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="npx", # Executable
        args=["-y", "@modelcontextprotocol/server-filesystem", working_directory], # Optional command line arguments
        env=None # Optional environment variables
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            deps = AgentDeps(console=Console(), current_working_directory=working_directory)

            agent = await get_agent(model=model, deps=deps, session=session)

            message_history: list[ModelMessage] = []
            while True:
                prompt = Prompt.ask("You").strip()
                
                if not prompt:
                    continue

                if prompt.lower() in EXIT_COMMANDS:
                    break


                result = await agent.run(prompt, deps=deps, message_history=message_history)
                response = result.data
                
                deps.console.print(f"Agent: {response.message}")

                # Exit if LLM indicates conversation is over
                if response.end_conversation:
                    break

        
