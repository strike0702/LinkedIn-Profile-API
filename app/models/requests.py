from pydantic import BaseModel, Field


class ProfileRequest(BaseModel):
    url: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="LinkedIn profile URL or vanity slug",
        examples=["https://www.linkedin.com/in/john-doe/"],
    )
