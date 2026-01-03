"""
Lazy loading utilities for gotaglio
"""

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
openai = LazyImport("openai")
# openai_types_chat = LazyImport("openai.types.chat")
azure_ai_inference = LazyImport("azure.ai.inference")
azure_core_credentials = LazyImport("azure.core.credentials")
azure_identity = LazyImport("azure.identity")
azure_identity_aio = LazyImport("azure.identity.aio")
numpy = LazyImport("numpy")
tiktoken = LazyImport("tiktoken")
scipy_optimize = LazyImport("scipy.optimize")
