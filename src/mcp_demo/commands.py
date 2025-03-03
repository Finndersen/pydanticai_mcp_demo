from typing import Protocol

from mcp_demo.agent import AgentRunner

EXIT_COMMANDS = ["/quit", "/exit", "/q"]


class CommandHandler(Protocol):
    def __call__(self, arg: str, agent_runner: AgentRunner) -> None: ...


def handle_clear(arg: str, agent_runner: AgentRunner) -> None:
    agent_runner.clear_message_history()
    agent_runner.deps.console.print("Conversation history cleared.")


COMMAND_HANDLERS: dict[str, CommandHandler] = {
    "/clear": handle_clear,
}


def handle_special_command(command: str, agent_runner: AgentRunner) -> None:
    command = command.strip()
    if not command.startswith("/"):
        raise ValueError(f"Invalid command format: {command}")

    parts = command.split(maxsplit=1)
    cmd = parts[0]
    arg = parts[1] if len(parts) > 1 else ""

    if cmd not in COMMAND_HANDLERS:
        raise ValueError(f"Unknown command: {cmd}")

    COMMAND_HANDLERS[cmd](arg, agent_runner)
