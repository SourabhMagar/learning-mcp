# Learning MCP

A hands-on project for learning the **Model Context Protocol (MCP)** by building a Python MCP server and connecting it to a local LLM using Ollama.

This project demonstrates how an MCP client discovers tools, invokes them, and passes results to a local language model to answer natural-language requests.

## Features

- Python MCP server using the MCP Python SDK.
- Three example tools:
  - `add_numbers` — adds two integers.
  - `calculate_bmi` — calculates BMI from weight and height.
  - `get_current_directory` — returns the server's working directory.
- Python MCP client using STDIO transport.
- Local LLM integration with Ollama and Qwen3 8B.
- Dynamic tool discovery and execution without a paid hosted-model API key.

## Architecture

```text
User Prompt
    |
    v
Python Client (client.py) <----> Ollama / Qwen3 8B
    |
    | MCP over STDIO
    v
Python MCP Server (server.py)
    |
    v
Registered Python Tools
```

The Python client coordinates Ollama and the MCP server. The model selects tools based on the user's request, the client executes them through MCP, and the results are sent back to the model to generate a final response.

## Requirements

- Python 3.11 or newer recommended.
- [Ollama](https://ollama.com/) installed and running.
- Qwen3 8B available locally in Ollama.
- Node.js and npm, if you want to use MCP Inspector.

## Setup

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd learning-mcp
```

Replace `<YOUR_REPOSITORY_URL>` with your actual GitHub repository URL.

### 2. Create a virtual environment

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install "mcp[cli]" ollama
```

This project uses the MCP Python SDK 2.x API. If you encounter an import or API mismatch, refer to the [official MCP Python SDK documentation](https://py.sdk.modelcontextprotocol.io/).

### 4. Download the local model

```bash
ollama pull qwen3:8b
```

Verify that the model is installed:

```bash
ollama list
```

Make sure Ollama is running. If needed, start the Ollama application or run:

```bash
ollama serve
```

You can optionally check the local API:

```bash
curl http://localhost:11434/api/tags
```

## Run the Application

Activate the virtual environment, navigate to the project directory, and run:

```bash
python client.py
```

The client launches `server.py` as a subprocess, connects through STDIO, discovers available MCP tools, and lets Ollama choose tools based on your prompts.

### Example prompts

Try these prompts in the application:

- `Add 10 and 20.`
- `Calculate BMI for a person weighing 70 kg and measuring 1.75 meters.`
- `Tell me which directory the server is running in.`

Type `exit` or `quit` to stop the application.

## Test with MCP Inspector

MCP Inspector allows you to discover and test your MCP tools manually.

Make sure Node.js and npm are installed, then run:

```bash
mcp dev server.py
```

Open the local URL printed in the terminal. Use Inspector to list the tools and execute them individually.

## Project Structure

```text
learning-mcp/
├── server.py       # MCP server and tool definitions
├── client.py       # MCP client and Ollama tool-calling loop
├── .gitignore
└── README.md
```

## Important Notes

- Ollama's local API normally runs at `http://localhost:11434`.
- No paid model API key is required for the local Ollama workflow.
- Do not commit `.venv`, credentials, `.env` files, or other secrets.
- Tools that access files, execute commands, or modify data should have appropriate validation, authorization, and user approval.
- This is a learning project intended to demonstrate MCP fundamentals and local LLM integration.

## Learning Goals

This project covers:

1. MCP server and client architecture.
2. Tool registration and discovery.
3. STDIO transport.
4. MCP tool execution.
5. Integrating a local LLM with MCP tools.
6. The tool-calling loop between the LLM, client, and server.

## Resources

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Ollama](https://ollama.com/)
- [Ollama Python Library](https://github.com/ollama/ollama-python)

## License

No license has been specified yet. Add a `LICENSE` file if you want to grant others explicit permission to use, modify, and distribute this project.
