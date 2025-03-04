from dataclasses import dataclass
from pathlib import Path
from rich.console import Console


@dataclass
class AgentDeps:
    current_working_directory: Path
    console: Console
