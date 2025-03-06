import inspect
import types
from typing import Any, Dict

from mcp import ClientSession
from mcp import Tool as MCPTool
from mcp.types import TextContent
from pydantic_ai import RunContext, Tool

from mcp_agent.deps import AgentDeps
from mcp_agent.util.filter_ignored_files import filter_directory_tree, filter_search_results
from mcp_agent.util.schema_to_params import convert_schema_to_params


async def get_tools(session: ClientSession) -> list[Tool[AgentDeps]]:
    """
    Get all tools from the MCP session and convert them to Pydantic AI tools.
    """
    tools_result = await session.list_tools()
    return [pydantic_tool_from_mcp_tool(session, tool) for tool in tools_result.tools]


def pydantic_tool_from_mcp_tool(session: ClientSession, tool: MCPTool) -> Tool[AgentDeps]:
    """
    Convert a MCP tool to a Pydantic AI tool.
    """
    tool_function = create_function_from_schema(session=session, name=tool.name, schema=tool.inputSchema)
    return Tool(name=tool.name, description=tool.description, function=tool_function, takes_ctx=True)


def create_function_from_schema(session: ClientSession, name: str, schema: Dict[str, Any]) -> types.FunctionType:
    """
    Create a function with a signature based on a JSON schema. This is necessary because PydanticAI does not yet
    support providing a tool JSON schema directly.

    Args:
        session: The MCP client session
        name: Name for the generated function
        schema: A JSON schema describing the function parameters

    Returns:
        A dynamically created function with the appropriate signature
    """
    # Create parameter list from tool schema
    parameters = convert_schema_to_params(schema)

    # Create the signature
    sig = inspect.Signature(parameters=parameters)

    # Create function body
    async def function_body(ctx: RunContext[AgentDeps], **kwargs) -> str:
        if name == "search_files":
            kwargs["excludePatterns"] = kwargs.get("excludePatterns", []) + [".venv", ".git"]
            
        ctx.deps.console.print(f"[blue]Calling tool[/blue] [bold]{name}[/bold] with arguments: {kwargs}")

        # Call the MCP tool with provided arguments
        result = await session.call_tool(name, arguments=kwargs)

        if result.isError:
            ctx.deps.console.print(f"[red]Tool {name} returned an error:[/red]")
        else:
            ctx.deps.console.print(f"[green]Tool[/green] [bold]{name}[/bold] returned:")
            # Filter the result if the tool is directory_tree
            if name == "search_files":
                result = filter_search_results(result)

        ctx.deps.console.print(result)
        # Return text for TextContent
        if isinstance(result.content[0], TextContent):
            return result.content[0].text
        else:
            raise ValueError("Expected TextContent, got ", type(result.content[0]))

    # Create the function with the correct signature
    dynamic_function = types.FunctionType(
        function_body.__code__,
        function_body.__globals__,
        name=name,
        argdefs=function_body.__defaults__,
        closure=function_body.__closure__,
    )

    # Add signature and annotations
    dynamic_function.__signature__ = sig  # type: ignore
    dynamic_function.__annotations__ = {param.name: param.annotation for param in parameters}

    return dynamic_function
