###############################################################################
#
# THIS CODE WORKS FOR ALL DEPLOYMENTS SHOWN BELOW
#
#
###############################################################################

# Reusable template for connecting to Azure Foundry OpenAI models locally

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import os

# --- Step 1: Get these values from the Azure Foundry portal ---

# The deployment name for your model (e.g., "gpt-5-mini", "my-custom-model")
deployment_name = "gpt-5-mini" 
deployment_name = "DeepSeek-V3.1" 
deployment_name = "gpt-4.1" 

# The endpoint from the portal. It might look like:
# https://your-foundry.openai.azure.com/openai/v1/
portal_endpoint = "https://mhop-foundry.openai.azure.com/openai/v1/"


# --- Step 2: Convert the portal values into the correct format ---

# Use a recent, stable API version. This one is a good default.
api_version = "2024-02-15-preview"

# Remove the trailing "/openai/v1/" to get the base endpoint.
azure_endpoint = portal_endpoint.split("/openai/")[0]


# --- Step 3: Set up the AzureOpenAI client ---

# Get a token provider using your default Azure credentials.
# This assumes you are logged in with `az login` in your terminal.
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), 
    "https://cognitiveservices.azure.com/.default"
)

# Initialize the correct client for Azure.
client = AzureOpenAI(
    azure_endpoint=azure_endpoint,
    api_version=api_version,
    azure_ad_token_provider=token_provider,
    timeout=10.0
)


# --- Step 4: Make the API call ---

print(f"Connecting to deployment '{deployment_name}' at endpoint '{azure_endpoint}'...")

try:
    completion = client.chat.completions.create(
        model=deployment_name,  # Use the deployment name for the model
        messages=[
            {
                "role": "user",
                "content": "What is the capital of France?",
            }
        ],
    )

    print("\nResponse:")
    print(completion.choices[0].message.content)

except Exception as e:
    print(f"\nAn error occurred: {e}")
