
import os

from mcp.server.mcpserver import MCPServer

# Create our MCP server
mcp = MCPServer("learning-mcp", version="1.0.0")


@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two integers and return their sum."""
    return a + b


@mcp.tool()
def calculate_bmi(weight: float, height: float) -> float:
    """Calculate BMI using weight in kilograms and height in meters."""
    if weight <= 0 or height <= 0:
        raise ValueError("Weight and height must be positive.")

    return round(weight / (height ** 2), 2)


@mcp.tool()
def get_current_directory() -> str:
    """Return the current working directory of the server."""
    return os.getcwd()


if __name__ == "__main__":
    mcp.run(transport="stdio")
