###############################################################################
#
# THIS CODE WORKS FOR ALL DEPLOYMENTS SHOWN BELOW
#
###############################################################################

# from mcp.server.fastmcp import FastMCP
import asyncio
from fastmcp import FastMCP
import json
# if TYPE_CHECKING:
from openai.types.chat import ChatCompletionMessageParam
from pydantic import TypeAdapter

from gotaglio.mcp_tools import AzureFoundryModel, ModelConfig


raw_config = [
    {
        "name": "gpt-5-mini",
        "description": "GPT-5-mini",
        "type": "AZURE_OPEN_AI",
        "endpoint": "https://mhop-foundry.openai.azure.com",
        "deployment": "gpt-5-mini",
        "authentication": {"type": "oauth"},
        "api": "2024-02-15-preview",
    },
    {
        "name": "deepseek-v3.1",
        "description": "DeepSeek-V3.1",
        "type": "AZURE_OPEN_AI",
        "endpoint": "https://mhop-foundry.openai.azure.com",
        "deployment": "DeepSeek-V3.1",
        "authentication": {"type": "oauth"},
        "api": "2024-02-15-preview",
    },
    {
        "name": "gpt4o",
        "description": "gpt-4o-2024-11-20",
        "type": "AZURE_OPEN_AI",
        "endpoint": "https://mhop-azure-openai.openai.azure.com/",
        "deployment": "gpt-4o-2024-11-20",
        "authentication": {"type": "oauth"},
        "api": "2024-08-01-preview",
    },
]


def create_mcp_server():
    # Create an MCP server
    # Note: json_response should be passed to run() when starting the server remotely
    # mcp.run(json_response=True)
    # mcp.run("stdio", json_response=True)
    mcp = FastMCP("Demo")

    # Add an addition tool
    @mcp.tool()
    def add(a: int, b: int) -> int:
        print(f"=============> Adding {a} + {b}")
        """Add two numbers"""
        return a + b

    # Encode a string
    @mcp.tool()
    def hex_dump(a: str) -> str:
        """convert a string to its hexadecimal representation"""
        print(f"=============> Encoding {a}")
        return a.encode("utf-8").hex()

    return mcp


async def run_test():
    mcp_server = create_mcp_server()

    adapter = TypeAdapter(list[ModelConfig])
    validated_configs = adapter.validate_python(raw_config)
    print("Validated model configurations successfully.")

    for config in validated_configs:
        print("=" * 40)
        print(f"Testing model: {config.name}")
        model = AzureFoundryModel(config, mcp_server)
        messages: list[ChatCompletionMessageParam] = [
            {
                "role": "user",
                "content": 'Convert "hello, world!" to hexidecimal.',  # "What is the capital of France?",
            }
        ]

        await model.infer(messages)
        print(json.dumps(messages, indent=2))



def go():
    asyncio.run(run_test())


go()
