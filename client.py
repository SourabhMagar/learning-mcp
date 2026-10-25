import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.types import TextContent
from ollama import AsyncClient


MODEL = "qwen3:8b"
MAX_TOOL_ROUNDS = 5


def get_tool_text(result) -> str:
    """Convert an MCP tool result into text for the LLM."""
    parts = []

    for item in result.content:
        if isinstance(item, TextContent):
            parts.append(item.text)
        else:
            parts.append(str(item))

    text = "\n".join(parts)

    if result.is_error:
        return f"Tool execution failed: {text}"

    return text or "Tool returned no text content."


async def main():
    server_path = Path(__file__).with_name("server.py")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
    )

    ollama = AsyncClient()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant. Use the available tools "
                "when needed. Use the supplied resource information "
                "when relevant. Never claim a tool succeeded unless "
                "its result confirms success."
            ),
        }
    ]

    print(f"Connecting to MCP server and Ollama model {MODEL}...")

    async with Client(server_params) as mcp_client:
        # --------------------------------------------------
        # 1. Discover MCP tools
        # --------------------------------------------------
        mcp_result = await mcp_client.list_tools()
        mcp_tools = {
            tool.name: tool for tool in mcp_result.tools
        }

        print("\nAvailable tools:")
        for tool in mcp_result.tools:
            print(f"- {tool.name}: {tool.description or 'No description'}")

        # --------------------------------------------------
        # 2. Discover MCP resources
        # --------------------------------------------------
        resource_result = await mcp_client.list_resources()

        print("\nAvailable resources:")
        for resource in resource_result.resources:
            print(f"- {resource.name}: {resource.uri}")

        # --------------------------------------------------
        # 3. Read the project information resource
        # --------------------------------------------------
        resource_uri = "project://info"

        available_uris = {
            str(resource.uri)
            for resource in resource_result.resources
        }

        if resource_uri in available_uris:
            resource_content = await mcp_client.read_resource(
                resource_uri
            )

            resource_parts = []

            for item in resource_content.contents:
                if hasattr(item, "text") and item.text:
                    resource_parts.append(item.text)

            resource_text = "\n".join(resource_parts)

            print("\nProject resource content:")
            print(resource_text or "Resource returned no text content.")

            # Add resource information to the LLM's context.
            if resource_text:
                messages[0]["content"] += (
                    "\n\nProject information from the MCP resource "
                    f"{resource_uri}:\n{resource_text}"
                )
        else:
            print(f"\nResource {resource_uri} was not found.")

        # --------------------------------------------------
        # 4. Convert MCP tools to Ollama's tool format
        # --------------------------------------------------
        ollama_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or tool.name,
                    "parameters": tool.input_schema,
                },
            }
            for tool in mcp_result.tools
        ]

        print("\nConnected successfully!")
        print("Available tools:", ", ".join(mcp_tools))
        print("\nType 'exit' to quit.\n")

        # --------------------------------------------------
        # 5. Interactive chat and tool-calling loop
        # --------------------------------------------------
        while True:
            user_input = input("You: ").strip()

            if user_input.lower() in {"exit", "quit"}:
                break

            if not user_input:
                continue

            messages.append({
                "role": "user",
                "content": user_input,
            })

            for _ in range(MAX_TOOL_ROUNDS):
                response = await ollama.chat(
                    model=MODEL,
                    messages=messages,
                    tools=ollama_tools,
                    think=False,
                    options={"temperature": 0},
                )

                assistant_message = response.message
                messages.append(assistant_message)

                tool_calls = assistant_message.tool_calls or []

                # The model has produced its final answer.
                if not tool_calls:
                    print(
                        f"\nAssistant: {assistant_message.content}\n"
                    )
                    break

                # Execute each tool requested by the model.
                for tool_call in tool_calls:
                    name = tool_call.function.name
                    arguments = tool_call.function.arguments

                    print(f"\nCalling MCP tool: {name}")
                    print(f"Arguments: {arguments}")

                    if name not in mcp_tools:
                        tool_output = (
                            f"Error: Unknown tool '{name}'."
                        )
                    else:
                        try:
                            result = await mcp_client.call_tool(
                                name,
                                arguments,
                            )
                            tool_output = get_tool_text(result)

                        except Exception as exc:
                            tool_output = (
                                f"Tool call failed: "
                                f"{type(exc).__name__}: {exc}"
                            )

                    print(f"Tool result: {tool_output}")

                    messages.append({
                        "role": "tool",
                        "tool_name": name,
                        "content": tool_output,
                    })

            else:
                print(
                    "\nStopped after reaching the tool-call limit. "
                    "Try a simpler request.\n"
                )

    print("Disconnected from MCP server.")


if __name__ == "__main__":
    asyncio.run(main())