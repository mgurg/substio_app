from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_200_OK

from app.controller.offers import offer_router
from app.controller.places import place_router

origins = ["http://localhost", "http://localhost:8080", "*"]


def create_application() -> FastAPI:
    """
    Create base FastAPI app with CORS middlewares and routes loaded
    Returns:
        FastAPI: [description]
    """
    app = FastAPI(debug=False)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
        max_age=86400,
    )

    app.include_router(offer_router, prefix="/offers", tags=["OFFERS"])
    app.include_router(place_router, prefix="/places", tags=["PLACE"])

    return app


app = create_application()


@app.get("/")
async def read_root():
    return {"Hello": "World!"}


@app.get("/health",
         status_code=HTTP_200_OK,
         tags=["healthcheck"],
         summary="Perform a Health Check",
         response_description="Return HTTP Status Code 200 (OK)"
         )
async def health_check():
    return {"status": "healthy"}
