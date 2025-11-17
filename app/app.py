from fastapi import FastAPI

from app.orders import router as orders_router


app = FastAPI()


@app.get("/")
def health_check():
    return {"status": "ok"}


app.include_router(orders_router)
