from dataclasses import dataclass

from rich.console import Console


@dataclass
class AgentDeps:
    current_working_directory: str
    console: Console
