from ..registry import register_models2, Registry

def list_models() -> None:
    registry = Registry()
    register_models2(registry)
    print("Available models:")
    for k, v in registry._models.items():
        print(f"  {k}: {v.metadata()["description"]}")
