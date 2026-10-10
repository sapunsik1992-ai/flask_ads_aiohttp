from pydantic import BaseModel, Field, ValidationError

from errors import HttpError


class CreateAd(BaseModel):
    title: str = Field(..., min_length=1, description="заголовок")
    description: str = Field("", description="описание")
    owner: str = Field(..., min_length=1, description="владелец")


class UpdateAd(BaseModel):
    title: str | None = Field(None, min_length=1, description="заголовок")
    description: str | None = Field(None, description="описание")
    owner: str | None = Field(None, min_length=1, description="владелец")


def validate(data, schema_class):
    try:
        return schema_class.model_validate(data).model_dump()
    except ValidationError as e:
        raise HttpError(str(e), 400) from e
