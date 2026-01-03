###############################################################################
#
# THIS CODE WORKS FOR ALL DEPLOYMENTS SHOWN BELOW
#
###############################################################################

# from mcp.server.fastmcp import FastMCP
import asyncio
from fastmcp import FastMCP
from openai import AzureOpenAI
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from typing import Any, cast, Literal, Union

from gotaglio.mcp_tools import MCPModel, MCPTools, ModelConfig


raw_config = [
    # {
    #     "name": "gpt-5-mini",
    #     "description": "GPT-5-mini",
    #     "type": "AZURE_OPEN_AI",
    #     "endpoint": "https://mhop-foundry.openai.azure.com",
    #     "deployment": "gpt-5-mini",
    #     "authentication": {"type": "oauth"},
    #     "api": "2024-02-15-preview",
    # },
    # {
    #     "name": "deepseek-v3.1",
    #     "description": "DeepSeek-V3.1",
    #     "type": "AZURE_OPEN_AI",
    #     "endpoint": "https://mhop-foundry.openai.azure.com",
    #     "deployment": "DeepSeek-V3.1",
    #     "authentication": {"type": "oauth"},
    #     "api": "2024-02-15-preview",
    # },
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
    mcp = FastMCP("Demo", json_response=True)

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
    mcp = create_mcp_server()
    mcp_tools = MCPTools(mcp)

    adapter = TypeAdapter(list[ModelConfig])
    validated_configs = adapter.validate_python(raw_config)
    print("Validated model configurations successfully.")

    # Get a token provider using your default Azure credentials.
    # This assumes you are logged in with `az login` in your terminal.
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    print("Obtained Azure AD token provider successfully.")

    for config in validated_configs:
        print("=" * 40)
        print(
            f"Connecting to deployment '{config.deployment}' at endpoint '{config.endpoint}'..."
        )
        model = MCPModel(config, mcp_tools=mcp_tools)
        await model.infer(
            [
                {
                    "role": "user",
                    "content": 'Convert "hello, world!" to hexidecimal.' # "What is the capital of France?",
                }
            ]
        )

        # client = AzureOpenAI(
        #     azure_endpoint=config.endpoint,
        #     api_version=config.api,
        #     azure_ad_token_provider=token_provider,
        #     timeout=10.0,
        # )

        # try:
        #     completion = client.chat.completions.create(
        #         model=config.deployment,  # Use the deployment name for the model
        # messages=[
        #     {
        #         "role": "user",
        #         "content": "What is the capital of France?",
        #     }
        # ],
        #     )

        #     print("\nResponse:")
        #     print(completion.choices[0].message.content)

        # except Exception as e:
        #     print(f"\nAn error occurred: {e}")

def go():
    asyncio.run(run_test()) 

go()
