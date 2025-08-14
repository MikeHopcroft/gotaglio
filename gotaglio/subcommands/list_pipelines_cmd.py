from gotaglio.pipeline_spec import PipelineSpecs


def list_pipelines(pipeline_specs: PipelineSpecs):
    print("Available pipelines:")
    for spec in pipeline_specs:
        print(f"  {spec.name}: {spec.description}")
