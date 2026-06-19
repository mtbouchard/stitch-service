"""Request/response schemas. No job model anymore - /stitch returns the image directly."""
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    id: str


class StitchRequest(BaseModel):
    # Exactly two ids (the script stages two hardcoded names). >=2 here; the route enforces ==2.
    images: list[str] = Field(min_length=2)
