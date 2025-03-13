from pathlib import Path

from mcp import ClientSession
from pydantic_ai import Agent
from pydantic_ai.models import Model

from mcp_agent.deps import AgentDeps
from mcp_agent.tools import get_tools


async def get_agent(model: Model, deps: AgentDeps, session: ClientSession) -> Agent[AgentDeps]:
    tools = await get_tools(session)
    prompt = get_system_prompt(deps.current_working_directory)
    agent = Agent(
        model=model,
        deps_type=type(deps),
        system_prompt=prompt,
        tools=tools,
    )
    return agent


PROMPT_TEMPLATE = """
# IDENTITY AND PURPOSE

You are a helpful assistant with strong software development and engineering skills,
whos purpose is to help the user with their software development or general file editing needs.


# IMPORTANT RULES AND EXPECTED BEHAVIOUR

* If the user request is unclear, ambigious or invalid, ask clarifying questions.
* Use the tools provided to obtain any information or perform any actions necessary to complete the user's request.
* Don't assume what type of project the user is working on if it is not evident from the request.
    Use the available tools or ask to find out if required.


# EXAMPLE BEHAVIOUR

-------


# CONTEXTUAL INFORMATION

Current working directory: {current_working_directory}
Directory listing:
{directory_listing}

"""


def get_system_prompt(current_working_directory: Path) -> str:
    directory_listing = "\n".join(
        sorted([p.name + "/" for p in current_working_directory.iterdir() if p.is_dir()])
        + sorted([p.name for p in current_working_directory.iterdir() if not p.is_dir()])
    )
    return PROMPT_TEMPLATE.format(
        current_working_directory=str(current_working_directory), directory_listing=directory_listing
    )
