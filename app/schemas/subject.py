from pydantic import BaseModel

class SubjectBase(BaseModel):
    name: str

class Subject(SubjectBase):
    id: int

    class Config:
        from_attributes = True