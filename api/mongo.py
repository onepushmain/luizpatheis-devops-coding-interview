from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from typing import Any
from bson import ObjectId
from pydantic_core import core_schema
from functools import lru_cache


class PyObjectId(str):
    """
    helper to map ObjectId to string and viceversa

    taken from https://stackoverflow.com/a/77105412
    """

    @classmethod
    def __get_pydantic_core_schema__(
            cls, _source_type: Any, _handler: Any
    ) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )

    @classmethod
    def validate(cls, value) -> ObjectId:
        if not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId")

        return ObjectId(value)


@lru_cache
def get_db_client(uri: str) -> MongoClient:
    db_client = MongoClient(uri)

    return db_client


def get_db(client: MongoClient, db_name: str | None = None) -> Database:
    db = client.get_database(db_name)

    return db


def get_collection(db: Database, name: str) -> Collection:
    collection = db.get_collection(name)

    return collection

