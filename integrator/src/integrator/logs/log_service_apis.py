from fastapi import APIRouter, Body
from integrator.utils.logger import get_logger

logger = get_logger(__name__)

log_router = APIRouter(
    prefix="/logs",
    tags=["logs"],
)

@log_router.post("/")
async def receive_log(message: str = Body(..., embed=True)):
    """
    Receives a log message from the frontend and logs it on the backend.
    """
    logger.info(f"Frontend log: {message}")
    return {"status": "logged"}
