from ..registry import register_models, Registry

def list_models() -> None:
    registry = Registry()
    register_models(registry)
    print("Available models:")
    for k, v in registry._models.items():
        print(f"  {k}: {v.metadata()["description"]}")
