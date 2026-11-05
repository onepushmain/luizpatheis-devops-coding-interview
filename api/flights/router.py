from fastapi import APIRouter, Depends
from api.flights.models import Flight, FlightCreate
import api.flights.service as service
from api.mongo import Collection
from api.dependencies import build_collection_getter_dependency

flights_router = APIRouter()

get_collection = build_collection_getter_dependency(collection='flights')


@flights_router.get('/flights', tags=["flights"], response_model=list[Flight], response_model_by_alias=False)
def get_flights(skip: int = 0, limit: int = 100, coll: Collection = Depends(get_collection)):
    return service.get_flights(coll=coll, skip=skip, limit=limit)


@flights_router.post('/flights', tags=["flights"], response_model=Flight, response_model_by_alias=False)
def create_flight(flight: FlightCreate, coll: Collection = Depends(get_collection)):
    return service.create_flight(coll=coll, flight=flight)
