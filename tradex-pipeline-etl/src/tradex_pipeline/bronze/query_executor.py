from typing import Any, Callable, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from tradex_pipeline.bronze.jobs.arxiv_papers import arxiv_call


# Map of available job functions
JOBS: Dict[str, Callable[..., Any]] = {
    "arxiv.papers": arxiv_call,
}


class QueryRequest(BaseModel):
    source: str = Field(..., description="Job source key, e.g. 'arxiv.papers'")
    params: Dict

class QueryResponse(BaseModel):
    source: str
    result: Any


app = FastAPI(title="Query Executor API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/sources")
def list_sources():
    return {"sources": sorted(JOBS.keys())}


@app.post("/query", response_model=QueryResponse)
def query_call_endpoint(payload: QueryRequest):
    func = JOBS.get(payload.source)
    if not func:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source: {payload.source}. Valid sources: {sorted(JOBS.keys())}",
        )

    try:
        result = func(payload=payload)
    except Exception as e:
        # You can log e here if you have logging set up
        raise HTTPException(status_code=500, detail=f"Job execution failed: {str(e)}")

    return QueryResponse(source=payload.source, result=result)