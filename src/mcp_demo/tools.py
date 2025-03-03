import inspect
import types
from typing import Any, Dict

from mcp.types import CallToolResult
from pydantic_ai import RunContext, Tool
from mcp import Tool as MCPTool
from mcp import ClientSession

from mcp_demo.deps import AgentDeps

    # Map JSON schema types to Python types
TYPE_MAP = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None)
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
    # Extract properties from schema
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    
    # Create parameter list (initially contains only the run context parameter)
    parameters: list[inspect.Parameter] = [inspect.Parameter(
                    name="ctx",
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=RunContext[AgentDeps]
                )]
    param_annotations = {}
    
    for param_name, param_info in properties.items():
        param_type = TYPE_MAP.get(param_info.get("type", "string"), Any)
        param_annotations[param_name] = param_type
        
        # Required parameters don't have default values
        if param_name in required:
            parameters.append(
                inspect.Parameter(
                    name=param_name,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=param_type
                )
            )
        else:
            # Optional parameters get a default value of None
            parameters.append(
                inspect.Parameter(
                    name=param_name,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=None,
                    annotation=param_type
                )
            )
    
    # Create the signature
    sig = inspect.Signature(parameters=parameters)
    
    # Create function body
    async def function_body(ctx: RunContext[AgentDeps], **kwargs) -> CallToolResult:
        bound_args = sig.bind(**kwargs)
        bound_args.apply_defaults()
        ctx.deps.console.print(f"[blue]Calling tool[/blue] [bold]{name}[/bold] with arguments:")
        ctx.deps.console.print(bound_args.kwargs)
        # Call the MCP tool
        result = await session.call_tool(name, arguments=bound_args.kwargs)
        if result.isError:
            raise Exception(f"[red]Tool {name} returned an error:[/red]")
        else:
            ctx.deps.console.print(f"[green]Tool[/green] [bold]{name}[/bold] returned:")
        ctx.deps.console.print(result)
        return result
        
    
    # Create the function with the correct signature
    dynamic_function = types.FunctionType(
        function_body.__code__,
        function_body.__globals__,
        name=name,
        argdefs=function_body.__defaults__,
        closure=function_body.__closure__
    )
    
    # Add signature and annotations
    dynamic_function.__signature__ = sig    # type: ignore
    dynamic_function.__annotations__ = param_annotations
    
    return dynamic_function


def pydantic_tool_from_mcp_tool(session: ClientSession, tool: MCPTool) -> Tool[AgentDeps]:
    """
    Convert a MCP tool to a Pydantic AI tool.
    """
    tool_function = create_function_from_schema(session=session, name=tool.name, schema=tool.inputSchema)
    return Tool(
        name=tool.name,
        description=tool.description,
        function=tool_function,
        takes_ctx=True
    )
    
async def get_tools(session: ClientSession) -> list[Tool[AgentDeps]]:
    """
    Get all tools from the MCP session and convert them to Pydantic AI tools.
    """
    tools_result = await session.list_tools()
    return [pydantic_tool_from_mcp_tool(session, tool) for tool in tools_result.tools]