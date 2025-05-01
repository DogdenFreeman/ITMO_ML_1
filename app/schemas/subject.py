from pydantic import BaseModel, ConfigDict


class SubjectBase(BaseModel):
    name: str


class Subject(SubjectBase):
    id: int

    model_config = ConfigDict(from_attributes=True)