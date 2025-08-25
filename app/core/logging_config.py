import logging
import sys
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging (can also be configured in a separate logging config file)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("user-info")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log Request
        logger.info(
            f"Request: {request.method} {request.url} " f"Client: {request.client.host}"
        )

        # Get response
        response = await call_next(request)

        process_time = (time.time() - start_time) * 1000
        formatted_time = f"{process_time:.2f}ms"

        # Log Response
        logger.info(
            f"Response: status_code={response.status_code} "
            f"Method={request.method} Path={request.url.path} "
            f"Time={formatted_time}"
        )

        return response
