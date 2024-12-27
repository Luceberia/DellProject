import asyncio
from exceptions.network_exceptions import TimeoutError
from dell_logging.log_config import logger, setup_logging

setup_logging()

async def run_with_timeout(coro, timeout):
    try:
        return await asyncio.wait_for(coro, timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout} seconds")