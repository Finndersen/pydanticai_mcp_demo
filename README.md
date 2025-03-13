# AI Agent with MCP Demo

This is a demonstration of how to use [Model Context Protocol (MCP)](https://www.anthropic.com/news/model-context-protocol) to add capabilties to a [Pydantic AI](https://ai.pydantic.dev/) Agent. 
Currently the framework does not natively support MCP or even directly specifying tool definition schemas, so it's not so straightforward.

The agent will be provided tools for interacting with the filesystem, via an MCP server based on the official reference implementation [here](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem). 

## Requirements

- [uv](https://docs.astral.sh/uv/)
- [node.js](https://nodejs.org/en/download)

## Installation

Clone this repo then run:

```bash
make install
```

## Usage

Coonfigure your `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` or `GEMINI_API_KEY`, then run the interactive CLI:

```bash
make run
```

Tell the agent what you would like it to do! It will have access to the following tools:
- read file(s)
- write/edit/move files
- create & list directories
- search files