from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, List
from datetime import datetime
from langchain.schema import Document


class WorkflowState(BaseModel):
    """State for the fpl gaffer workflow."""

    # Core state variables
    stage: Literal["extraction", "processing", "decision"] = "collector"
    gameweek: Optional[int] = None
    deadline: Optional[datetime] = None
    error_log: Optional[List[str]] = Field(default_factory=list)

    # Data extraction stage variables
    fpl_data: Dict = Field(default_factory=dict)
    news_search_data: List[Document] = Field(default_factory=list)
    user_data: Dict = Field(default_factory=dict)

    # Data processing stage variables
    filtered_news: List[Document] = Field(default_factory=list)

    # Decision stage variables
    # TODO: Determine decision agent output structure
