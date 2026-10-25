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


async def read_mcp_resource(mcp_client, uri: str) -> str:
    """Read a text resource through the MCP client."""
    result = await mcp_client.read_resource(uri)

    parts = []

    for item in result.contents:
        if hasattr(item, "text") and item.text:
            parts.append(item.text)

    return "\n".join(parts) or "Resource returned no text content."


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
                "You are a helpful assistant connected to an MCP server. "
                "Use available MCP tools when appropriate. "
                "Use the read_mcp_resource function when you need "
                "information from an MCP resource. Only request resource "
                "URIs listed in the available resources. "
                "Use tool and resource results accurately. "
                "Never claim an operation succeeded unless its result "
                "confirms success."
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

        print("\nAvailable MCP tools:")
        for tool in mcp_result.tools:
            print(f"- {tool.name}: {tool.description or 'No description'}")

        # --------------------------------------------------
        # 2. Discover MCP resources
        # --------------------------------------------------
        resource_result = await mcp_client.list_resources()

        resources_by_uri = {
            str(resource.uri): resource
            for resource in resource_result.resources
        }

        resource_uris = list(resources_by_uri.keys())

        print("\nAvailable MCP resources:")
        for uri, resource in resources_by_uri.items():
            print(f"- {uri}: {resource.name}")

        if resources_by_uri:
            resource_descriptions = "\n".join(
                f"- URI: {uri}; "
                f"Name: {resource.name}; "
                f"Description: {resource.description or 'Not provided'}"
                for uri, resource in resources_by_uri.items()
            )

            messages[0]["content"] += (
                "\n\nAvailable MCP resources:\n"
                + resource_descriptions
                + "\nUse a resource when its content is relevant."
            )

        # --------------------------------------------------
        # 3. Discover MCP prompts
        # --------------------------------------------------
        prompt_result = await mcp_client.list_prompts()

        prompts_by_name = {
            prompt.name: prompt
            for prompt in prompt_result.prompts
        }
        print("\nDEBUG - Prompts returned by server:")

        for prompt in prompt_result.prompts:
            print(f"Name: {prompt.name}")
            print(f"Description: {prompt.description}")

        print("\nAvailable MCP prompts:")
        for prompt in prompt_result.prompts:
            print(f"- {prompt.name}: {prompt.description or 'No description'}")

        # --------------------------------------------------
        # 4. Convert MCP tools into Ollama tool definitions
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

        # --------------------------------------------------
        # 5. Add a client-side resource-reading function
        # --------------------------------------------------
        if resource_uris:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": "read_mcp_resource",
                    "description": (
                        "Read an available MCP resource when you need "
                        "its contents to answer the user's question."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "uri": {
                                "type": "string",
                                "enum": resource_uris,
                                "description": "URI of the resource to read.",
                            }
                        },
                        "required": ["uri"],
                    },
                },
            })

        print("\nConnected successfully!")
        print("Type a question to chat.")
        print("Commands:")
        print("  /resources              - List available resources")
        print("  /prompts                - List available prompts")
        print("  /prompt resources       - Run explain_project with topic=resources")
        print("  /prompt <topic>         - Run explain_project for another topic")
        print("  exit                    - Quit\n")

        # --------------------------------------------------
        # 6. Interactive chat loop
        # --------------------------------------------------
        while True:
            user_input = input("You: ").strip()

            if user_input.lower() in {"exit", "quit"}:
                break

            if not user_input:
                continue

            # List resources on demand.
            if user_input == "/resources":
                for uri, resource in resources_by_uri.items():
                    print(f"- {uri}: {resource.name}")
                print()
                continue

            # List prompts on demand.
            if user_input == "/prompts":
                for prompt in prompts_by_name.values():
                    print(f"- {prompt.name}: {prompt.description or 'No description'}")
                print()
                continue

            # Retrieve an MCP prompt and send its messages to Ollama.
            if user_input.startswith("/prompt "):
                topic = user_input[len("/prompt "):].strip()

                if not topic:
                    print("Please provide a topic, e.g. /prompt resources\n")
                    continue

                if "explain_project" not in prompts_by_name:
                    print("The MCP prompt 'explain_project' is not available.\n")
                    continue

                try:
                    prompt_response = await mcp_client.get_prompt(
                        "explain_project",
                        arguments={"topic": topic},
                    )

                    # Convert returned MCP prompt messages into Ollama messages.
                    prompt_messages = []

                    for prompt_message in prompt_response.messages:
                        content = prompt_message.content

                        if isinstance(content, TextContent):
                            prompt_text = content.text
                        elif hasattr(content, "text"):
                            prompt_text = content.text
                        else:
                            prompt_text = str(content)

                        role = getattr(prompt_message, "role", "user")

                        # Map MCP prompt roles to Ollama chat roles.
                        if role not in {"user", "assistant", "system"}:
                            role = "user"

                        prompt_messages.append({
                            "role": role,
                            "content": prompt_text,
                        })

                    if not prompt_messages:
                        print("The MCP prompt returned no messages.\n")
                        continue

                    print(f"\nRetrieved MCP prompt: explain_project ({topic})")

                    prompt_chat = [
                        messages[0],
                        *prompt_messages,
                    ]

                    response = await ollama.chat(
                        model=MODEL,
                        messages=prompt_chat,
                        think=False,
                        options={"temperature": 0},
                    )

                    print(f"\nAssistant: {response.message.content}\n")

                except Exception as exc:
                    print(
                        f"Prompt request failed: "
                        f"{type(exc).__name__}: {exc}\n"
                    )

                continue

            # Add a normal user message to the ongoing conversation.
            messages.append({
                "role": "user",
                "content": user_input,
            })

            # --------------------------------------------------
            # 7. LLM tool/resource calling loop
            # --------------------------------------------------
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

                # The model produced a final answer.
                if not tool_calls:
                    print(f"\nAssistant: {assistant_message.content}\n")
                    break

                # Execute each requested function.
                for tool_call in tool_calls:
                    name = tool_call.function.name
                    arguments = tool_call.function.arguments

                    # Handle client-side resource reading.
                    if name == "read_mcp_resource":
                        uri = arguments.get("uri", "")

                        print(f"\nReading MCP resource: {uri}")

                        if uri not in resources_by_uri:
                            tool_output = (
                                f"Error: Resource URI '{uri}' "
                                "is not available."
                            )
                        else:
                            try:
                                tool_output = await read_mcp_resource(
                                    mcp_client,
                                    uri,
                                )
                            except Exception as exc:
                                tool_output = (
                                    f"Resource read failed: "
                                    f"{type(exc).__name__}: {exc}"
                                )

                    # Handle actual MCP server tools.
                    elif name in mcp_tools:
                        print(f"\nCalling MCP tool: {name}")
                        print(f"Arguments: {arguments}")

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

                    else:
                        tool_output = f"Error: Unknown function '{name}'."

                    print(f"Result: {tool_output}")

                    # Return the result to the model on the next round.
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