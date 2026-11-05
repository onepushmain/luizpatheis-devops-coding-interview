from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from api.mongo import PyObjectId


class FlightStatusEnum(str, Enum):
    cancelled = 'cancelled'
    scheduled = 'scheduled'


class FlightBase(BaseModel):
    status: FlightStatusEnum


class FlightCreate(FlightBase):
    pass


class Flight(FlightBase):
    id: PyObjectId = Field(alias='_id')

    model_config = ConfigDict(arbitrary_types_allowed=True)
