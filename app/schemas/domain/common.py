from pydantic import BaseModel, ConfigDict


class HealthCheck(BaseModel):
    status: str = "OK"


class BaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
