from typing import Literal, Optional, List, Dict
from pydantic import BaseModel, Field, ValidationError

import arxiv

class ArxivParams(BaseModel):
    sortBy: Literal["submittedDate", "lastUpdatedDate", "relevance"] = "submittedDate"
    sortOrder: Literal["ascending", "descending"] = "descending"
    max_results: int = Field(default=10, ge=1, le=30000)
    since_date: Optional[str] = None  # YYYYMMDDTTTT
    until_date: Optional[str] = None  # YYYYMMDDTTTT
    id_list: Optional[str] = None

class QueryRequest(BaseModel):
    source: str = Field(..., description="Job source key, e.g. 'arxiv.papers'")
    params: ArxivParams


def arxiv_call(payload: QueryRequest):
    params = payload.params or {}
    try:
        if hasattr(ArxivParams, "model_validate"):
            validated_params = ArxivParams.model_validate(params)
        else:
            validated_params = ArxivParams.parse_obj(params)
    except ValidationError as exc:
        raise ValueError(f"Invalid params for arxiv_call: {exc}") from exc

    # sort_by_options = {
    #     "submittedDate" : arxiv.SortCriterion.SubmittedDate,
    #     "lastUpdatedDate" : arxiv.SortCriterion.lastUpdatedDate,
    #     "relevance" : arxiv.SortCriterion.relevance,
    # }
    # sort_order_options = {
    #     "ascending" : arxiv.SortCriterion.SubmittedDate,
    #     "descending" : arxiv.SortCriterion.lastUpdatedDate,
    # }

    try:
        validated_params.query
    except Exception as e:
        print(e)

    query = validated_params.query
    print("a")
    sort_by = sort_by_options[validated_params.sort_by]
    sort_order = sort_order_options[validated_params.sort_order]
    max_results = validated_params.max_results

    print(query, sort_by, sort_order, max_results)
    
    return

    search = arxiv.Search(
        query=query,
        sort_by=sort_by,
        sort_order=sort_order,
        max_results=max_results,
    )


    return search
