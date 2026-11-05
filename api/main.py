from fastapi import FastAPI
from flights.router import flights_router

app = FastAPI()


@app.get('/', status_code=204, tags=["liveness"])
def health():
    pass


app.include_router(flights_router)
