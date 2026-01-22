"""
Lazy loading utilities for gotaglio
"""
from typing import TYPE_CHECKING

class LazyImport:
    """Lazy import wrapper that delays import until first access"""
    
    def __init__(self, module_name):
        self.module_name = module_name
        self._module = None
    
    def __getattr__(self, name):
        if self._module is None:
            self._module = __import__(self.module_name, fromlist=[name])
        return getattr(self._module, name)

# Lazy imports for heavy dependencies
if TYPE_CHECKING:
    import openai as openai
    import azure.ai.inference as azure_ai_inference
    import azure.core.credentials as azure_core_credentials
    import azure.identity as azure_identity
    import azure.identity.aio as azure_identity_aio
    import numpy as numpy
    import tiktoken as tiktoken
    import scipy.optimize as scipy_optimize
else:
    openai = LazyImport("openai")
    azure_ai_inference = LazyImport("azure.ai.inference")
    azure_core_credentials = LazyImport("azure.core.credentials")
    azure_identity = LazyImport("azure.identity")
    azure_identity_aio = LazyImport("azure.identity.aio")
    numpy = LazyImport("numpy")
    tiktoken = LazyImport("tiktoken")
    scipy_optimize = LazyImport("scipy.optimize")
