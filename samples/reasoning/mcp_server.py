from fastmcp import FastMCP
from typing import Annotated

# Create an MCP server
# Note: json_response should be passed to run() when starting the server remotely
# mcp.run(json_response=True)
# mcp.run("stdio", json_response=True)
mcp = FastMCP("Demo")

# Add an addition tool
@mcp.tool()
def stage1(a: Annotated[str, "Input string"]) -> str:
    """Run stage one processing"""
    # print(f'============> stage1("{a}")')
    return a[::-1]


# Encode a string
@mcp.tool()
def stage2(a: str) -> str:
    """Run stage two processing"""
    # print(f'============> stage2("{a}")')
    return a.upper() # + '!' # uncomment to cause failure.

if __name__ == "__main__":
    mcp.run()
