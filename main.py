import uvicorn

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from app.log import Log
from app.routers.career_pages import router as career_pages
from app.routers.job import router as job
from app.settings import config


def get_app():
    application = FastAPI(
        title="job scraper",
        description="help me get a job",
        version=f"{config.API_VERSION}-{config.IMAGE_TAG}",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(career_pages)
    application.include_router(job)

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        Log.error(str(exc.detail))
        return JSONResponse(str(exc.detail), status_code=exc.status_code)

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        error_detail = jsonable_encoder(exc.errors())

        Log.error(
            f"Failed request details: {request.method} "
            f"request to {request.url} "
            f"Error message: {error_detail}"
            f"Request metadata\n"
            f"\tPath Params: {request.path_params}\n"
            f"\tQuery Params: {request.query_params}\n"
        )

        return await request_validation_exception_handler(request, exc)

    @application.exception_handler(ValueError)
    async def value_error_exception_handler(request: Request, exc: ValueError):
        error_detail = jsonable_encoder(exc)

        Log.error(
            f"Failed request details: {request.method} "
            f"request to {request.url} "
            f"Error message: {error_detail}"
            f"Request metadata\n"
            f"\tPath Params: {request.path_params}\n"
            f"\tQuery Params: {request.query_params}\n"
        )

        Log.error(str(exc))
        return JSONResponse(str(exc), status_code=400)

    return application


application = get_app()


@application.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    Log.setup(application_name="quack-api")

    uvicorn.run(
        "main:application",
        host=config.BASE_URL,
        port=config.PORT,
        workers=config.NUM_WORKERS,
        reload=True,
        proxy_headers=True,
        forwarded_allow_ips="*",
        # TODO : ENABLE THIS AFTER LOG SETUP IS DONE
        # log_config=log_config,
    )
