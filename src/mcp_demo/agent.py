from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, AsyncIterator

from mcp import ClientSession
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models import Model

from mcp_demo.deps import AgentDeps
from mcp_demo.tools import get_tools


class LLMResponse(BaseModel):
    """
    Structured response format for the LLM to use so it can indicate when the conversation should end
    """

    message: str
    end_conversation: Annotated[
        bool,
        "Always set to true unless you are asking a question.",
    ]



async def get_agent(model: Model, deps: AgentDeps, session: ClientSession) -> Agent[AgentDeps, LLMResponse]:

    tools = await get_tools(session)
    agent = Agent(
        model=model,
        deps_type=type(deps),
        system_prompt=get_system_prompt(deps.current_working_directory),
        result_type=LLMResponse,
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
* If you have completed the users request and have no further questions to ask, set the `end_conversation` field to `True`.
* Don't assume what type of project the user is working on if it is not evident from the request. Use the available tools or ask to find out if required.


# EXAMPLE BEHAVIOUR

-------


# CONTEXTUAL INFORMATION

Current working directory: {current_working_directory}
Directory listing:
{directory_listing}

"""


def get_system_prompt(current_working_directory: str) -> str:
    directory_listing = "\n".join(
        sorted([p.name + "/" for p in Path(current_working_directory).iterdir() if p.is_dir()]) +
        sorted([p.name for p in Path(current_working_directory).iterdir() if not p.is_dir()])
    )
    return PROMPT_TEMPLATE.format(current_working_directory=current_working_directory, directory_listing=directory_listing)
