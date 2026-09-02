from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class AskQuestionRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    session_id: str = Field(
        min_length=1,
        max_length=100,
    )

    question: str = Field(
        min_length=1,
        max_length=4000,
    )

