from ..models import register_models
from ..registry import Registry

def list_models():
    registry = Registry()
    register_models(registry)
    print("Available models:")
    for k, v in registry._models.items():
        print(f"  {k}: {v.metadata()["description"]}")
