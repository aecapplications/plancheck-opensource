"""Pydantic models for structured LLM outputs and the facts file shape."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

# One shared classification pass serves every code book, so this is the union
# of all books' sheet types (electrical types serve the CEC).
SheetType = Literal[
    "cover_sheet", "site_plan", "floor_plan", "elevation", "section", "detail",
    "foundation_plan", "roof_plan", "framing_plan", "structural_notes",
    "general_notes", "schedules", "electrical_plan", "plumbing_mechanical",
    "energy_title24", "panel_schedule", "one_line_diagram", "power_plan",
    "lighting_plan", "other",
]

# Sheet types worth a vision pass (drawings) vs a text pass (notes/schedules).
DRAWING_TYPES = {
    "site_plan", "floor_plan", "elevation", "section", "detail",
    "foundation_plan", "roof_plan", "framing_plan", "electrical_plan",
    "plumbing_mechanical", "one_line_diagram", "power_plan", "lighting_plan",
}
TEXT_TYPES = {
    "cover_sheet", "general_notes", "structural_notes", "schedules",
    "energy_title24", "panel_schedule",
}


class SheetInfo(BaseModel):
    page: int = Field(description="1-based PDF page number")
    sheet_id: Optional[str] = Field(default=None, description="Sheet number from title block, e.g. A2.1")
    sheet_title: Optional[str] = None
    sheet_type: SheetType
    is_text_dominant: bool = Field(description="True for notes/schedules; False for drawings")


class ProjectMeta(BaseModel):
    address: Optional[str] = None
    type: Optional[str] = None
    scope: Optional[str] = None
    stories: Optional[int] = None
    occupancy: Optional[str] = None
    design_wind_speed_mph: Optional[float] = None
    ground_snow_load_psf: Optional[float] = None
    seismic_design_category: Optional[str] = None
    soil_class: Optional[str] = None
    climate_zone: Optional[str] = None
    fire_hazard_severity_zone: Optional[str] = None

    def merge(self, other: "ProjectMeta | None") -> "ProjectMeta":
        if other is None:
            return self
        data = self.model_dump()
        for k, v in other.model_dump().items():
            if v is not None and data.get(k) is None:
                data[k] = v
        return ProjectMeta(**data)


class SheetIndex(BaseModel):
    sheets: list[SheetInfo]
    project: ProjectMeta


class CandidateFact(BaseModel):
    predicate: str = Field(description="A canonical predicate name from the vocabulary")
    value: bool = Field(default=True, description="True=asserted; False=explicitly contradicted")
    confidence: float = Field(ge=0.0, le=1.0)
    page: int
    sheet_id: Optional[str] = None
    evidence: str = Field(description="Verbatim quote (text) or visual observation (vision)")
    source: Literal["text", "vision"] = "vision"


class SheetExtraction(BaseModel):
    candidates: list[CandidateFact]
    project_updates: Optional[ProjectMeta] = None


class ReconciledFacts(BaseModel):
    project: ProjectMeta
    predicates: list[str]
    false_predicates: list[str]
