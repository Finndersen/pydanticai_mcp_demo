import inspect
import json
import types
from typing import Any, Dict
import git
from pathlib import Path

from mcp import ClientSession
from mcp import Tool as MCPTool
from mcp.types import CallToolResult, TextContent
from pydantic_ai import RunContext, Tool

from mcp_demo.deps import AgentDeps


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


# Map JSON schema types to Python types
TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}


def create_function_from_schema(session: ClientSession, name: str, schema: Dict[str, Any]) -> types.FunctionType:
    """
    Create a function with a signature based on a JSON schema.

    Args:
        schema: A JSON schema describing the function parameters
        function_name: Name for the generated function

    Returns:
        A dynamically created function with the appropriate signature
    """
    print(f"Creating '{name}' function from schema: {schema}")
    # Extract properties from schema
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    # Create parameter list (initially contains only the run context parameter)
    parameters: list[inspect.Parameter] = [
        inspect.Parameter(name="ctx", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=RunContext[AgentDeps])
    ]

    for param_name, param_info in properties.items():
        param_type = TYPE_MAP.get(param_info.get("type", "string"), Any)
        
        if param_type is list:
            list_subtype = param_info.get("items", {}).get("type", "string")
            param_type = list[TYPE_MAP.get(list_subtype, Any)]
            

        # Required parameters don't have default values
        if param_name in required:
            parameters.append(
                inspect.Parameter(name=param_name, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=param_type)
            )
        else:
            # Optional parameters get a default value of None
            parameters.append(
                inspect.Parameter(
                    name=param_name, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None, annotation=param_type
                )
            )

    # Create the signature
    sig = inspect.Signature(parameters=parameters)

    # Create function body
    async def function_body(ctx: RunContext[AgentDeps], **kwargs) -> CallToolResult:
        ctx.deps.console.print(f"[blue]Calling tool[/blue] [bold]{name}[/bold] with arguments: {kwargs}")
        # Call the MCP tool
        result = await session.call_tool(name, arguments=kwargs)
        if result.isError:
            ctx.deps.console.print(f"[red]Tool {name} returned an error:[/red]")
        else:
            ctx.deps.console.print(f"[green]Tool[/green] [bold]{name}[/bold] returned:")
        ctx.deps.console.print(result)
        
        # Filter the result if the tool is a directory_tree tool
        if name == "directory_tree":
            result = filter_ignored_files(result, ctx.deps)
            
        return result

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


def filter_ignored_files(result: CallToolResult, deps: AgentDeps) -> CallToolResult:
    """
    Filter out files that match rules in .gitignore.
    
    Args:
        result: The result of a "directory_tree" tool call
        
    Returns:
        CallToolResult: The result of the tool call with ignored files filtered out
    """
    # Try to get git repo from current directory or parents
    try:
        repo = git.Repo(Path.cwd(), search_parent_directories=True)
    except git.InvalidGitRepositoryError:
        # Not in a git repo, return the original result
        return result
        
    content = result.content[0]
    if not isinstance(content, TextContent):
        raise ValueError("Expected TextContent, got ", type(content))
    
    directory_tree = json.loads(content.text)
    filtered_directory_tree = filter_directory(directory_tree, deps.current_working_directory, repo)
    print("Filtered directory tree:", filtered_directory_tree)
    content.text = json.dumps(filtered_directory_tree)
    return result
    

def filter_directory(directory_tree: dict[str, Any], current_path: Path, repo: git.Repo) -> dict[str, Any]:
    """
    Filter out files that match rules in .gitignore.
    """
    children = [
        filter_directory(item, current_path / item["name"], repo) if item["type"] == "directory" 
        else item 
        for item in directory_tree["children"] 
        if not repo.ignored(current_path / item["name"])]
    directory_tree["children"] = children
    return directory_tree
