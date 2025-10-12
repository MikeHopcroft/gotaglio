import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
import threading

from .director import Director
from .pipeline_spec import PipelineSpec


class InferRequest(BaseModel):
    case: Dict[str, Any]
    turn: int


class ValidateResponse(BaseModel):
    valid: bool
    error: str | None = None


# Global variables to store the director and pipeline spec
_director: Director | None = None
_pipeline_spec: PipelineSpec | None = None

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Gotaglio API Server"}


@app.post("/api/infer")
async def infer(request: InferRequest):
    """
    Infer API that takes a test case and turn number.
    Currently returns a mock response.
    """
    if _director is None:
        raise HTTPException(status_code=500, detail="Director not initialized")
    result = await _director.process_one_case(request.case, turn=request.turn)
    return {
        "message": "Mock inference response",
        "case_id": request.case.get("uuid", "unknown"),
        "turn": request.turn,
        "result": result
    }


@app.post("/api/validate", response_model=ValidateResponse)
async def validate(data: Dict[str, Any]):
    """
    Validate API that checks if JSON object is valid according to pipeline schema.
    Currently returns a mock response.
    """
    # Mock validation logic - always return valid for now
    if not data:
        return ValidateResponse(valid=False, error="Empty data provided")
    
    # Mock: Check if data has required fields (this is just an example)
    if "case" not in data:
        return ValidateResponse(valid=False, error="Missing 'case' field")
    
    return ValidateResponse(valid=True, error=None)


def serve(pipeline_spec: PipelineSpec, director: Director, port: int = 8000):
    """
    Entry point to start the FastAPI server with uvicorn.
    
    Args:
        pipeline_spec: The pipeline specification to use
        director: The director instance for pipeline operations
        port: Port to run the server on (default: 8000)
    """
    global _director, _pipeline_spec
    _director = director
    _pipeline_spec = pipeline_spec
    
    print(f"Starting Gotaglio API server on port {port}")
    print(f"Pipeline: {pipeline_spec.name}")
    print(f"API endpoints:")
    print(f"  POST http://localhost:{port}/api/infer")
    print(f"  POST http://localhost:{port}/api/validate")
    print("")
    print("Press Ctrl+C to stop the server")
    
    # Run uvicorn server
    uvicorn.run(app, host="0.0.0.0", port=port)
