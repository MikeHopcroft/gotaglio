def list_pipelines(registry_factory):
    registry = registry_factory()
    print("Available pipelines:")
    for k, v in registry._pipelines.items():
        print(f"  {k}: {v._description}")
