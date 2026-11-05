from api.mongo import Collection
from .models import FlightCreate


def get_flights(coll: Collection, skip: int = 0, limit: int = 100):
    return coll.find().skip(0).limit(limit)


def create_flight(coll: Collection, flight: FlightCreate):
    result = coll.insert_one(flight.dict())

    inserted_flight = coll.find_one({'_id': result.inserted_id})

    return inserted_flight
