from dataclasses import dataclass
from datetime import datetime
import os
from typing import List, Optional, Any

from llm_client import LLMType, string_to_enum


@dataclass
class DiffData:
    """Represents diff data from a git repository."""

    patches: List[str]
    file_names: List[str]
    repo_name: str
    contents: List[str]
    url_type: str


@dataclass
class ReviewConfig:
    """Configuration for code review processing."""

    # Processing configuration
    per_file_analysis: bool = False
    analyze_whole_file: bool = False
    prompt_input: str = ""
    prompt_template_selected: Optional[str] = "code-review"
    selected_model: str = "o1-mini"
    stream_checked: bool = True

    # Metadata
    review_id: Optional[str] = None
    repo_name: Optional[str] = None
    url: Optional[str] = None
    url_type: Optional[str] = None
    created_at: Optional[datetime] = None
    project_id: Optional[str] = None


@dataclass
class ModelConfig:
    """Configuration for LLM model."""

    model_name: str
    client_type: LLMType

    @classmethod
    def from_model_name(cls, model_name: str) -> "ModelConfig":
        """Create ModelConfig from model name."""
        model_name = model_name or os.getenv("DEFAULT_LLM_MODEL")

        if "gpt" in model_name.lower():
            client_type = LLMType.OPENAI
        elif "llama" in model_name.lower():
            client_type = LLMType.OLLAMA
        elif "deepseek" in model_name.lower():
            client_type = LLMType.OLLAMA
        elif "claude" in model_name.lower():
            client_type = LLMType.CLAUDE
        else:
            client_type = string_to_enum(
                LLMType, os.getenv("DEFAULT_LLM_CLIENT", "openai")
            )

        return cls(model_name=model_name, client_type=client_type)


@dataclass
class AnalysisContext:
    """Context for analysis generation."""

    diffs: DiffData
    config: ReviewConfig
    review_id: str
    file_name: str
    patch: str
    idx: int


@dataclass
class Project:
    """User inputs to create a project."""

    name: str
    github_repo_url: str
    repo_validated: bool
