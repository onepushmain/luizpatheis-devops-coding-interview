import api.mongo
import api.settings
from fastapi import Depends


def get_settings():
    return api.settings.get_settings()


def get_db_client(
    settings: api.settings.Settings = Depends(get_settings)
):
    return api.mongo.get_db_client(settings.mongo_uri)


def get_db(
    settings: api.settings.Settings = Depends(get_settings),
    client: api.mongo.MongoClient = Depends(get_db_client)
):
    return api.mongo.get_db(client=client, db_name=settings.mongo_db_name)


def build_collection_getter_dependency(
    collection: str
):

    def getter(
        db: api.mongo.Database = Depends(get_db)
    ):
        return api.mongo.get_collection(db=db, name=collection)

    return getter
