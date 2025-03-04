import json
from pathlib import Path
from typing import Literal, TypedDict

import git
from mcp.types import CallToolResult, TextContent


class DirectoryItem(TypedDict):
    name: str
    type: Literal["directory", "file"]
    children: list["DirectoryItem"]


def filter_ignored_files(result: CallToolResult, working_directory: Path) -> CallToolResult:
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
    filtered_directory_tree = filter_items(directory_tree, working_directory, repo)
    content.text = json.dumps(filtered_directory_tree)
    return result


def filter_items(directory_items: list[DirectoryItem], current_path: Path, repo: git.Repo) -> list[DirectoryItem]:
    """
    Filter out files that match rules in .gitignore.
    """
    filtered_items = [
        filter_directory_children(item, current_path / item["name"], repo) if item["type"] == "directory" else item
        for item in directory_items
        if not (repo.ignored(current_path / item["name"]) or item["name"] == ".git")
    ]
    return filtered_items


def filter_directory_children(directory: DirectoryItem, current_path: Path, repo: git.Repo) -> DirectoryItem:
    directory["children"] = filter_items(directory["children"], current_path, repo)
    return directory
