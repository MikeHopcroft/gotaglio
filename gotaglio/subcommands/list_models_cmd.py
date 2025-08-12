def list_models(registry_factory):
    registry = registry_factory()
    print("Available models:")
    for k, v in registry._models.items():
        print(f"  {k}: {v.metadata()["description"]}")
