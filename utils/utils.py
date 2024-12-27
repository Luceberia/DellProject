import functools
import random
import time
import logging
import asyncio
import aiohttp
from typing import Dict, Any
from operator import getitem


def get_nested_value(data, keys, default='정보없음'):
    try:
        return functools.reduce(getitem, keys, data)
    except (KeyError, TypeError):
        return default

def convert_capacity(capacity: int, is_bytes: bool = False) -> str:
    try:
        if is_bytes:
            capacity_bytes = capacity
        else:
            capacity_bytes = capacity * 1024 * 1024  # MiB to Bytes

        if capacity_bytes >= 1024 * 1024 * 1024 * 1024:  # >= 1 TiB
            capacity_tib = capacity_bytes / (1024 * 1024 * 1024 * 1024)
            return f"{int(capacity_tib) if capacity_tib.is_integer() else f'{capacity_tib:.1f}'} TiB"
        elif capacity_bytes >= 1024 * 1024 * 1024:  # >= 1 GiB
            capacity_gib = capacity_bytes / (1024 * 1024 * 1024)
            return f"{int(capacity_gib) if capacity_gib.is_integer() else f'{capacity_gib:.1f}'} GiB"
        else:  # MiB
            capacity_mib = capacity_bytes / (1024 * 1024)
            return f"{int(capacity_mib) if capacity_mib.is_integer() else f'{capacity_mib:.1f}'} MiB"
    except (TypeError, ZeroDivisionError):
        return "용량정보없음"

def performance_logger(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logging.info(f"{func.__name__} 실행 시간: {execution_time:.2f}초")
        return result
    return wrapper

def exponential_backoff(attempt, base_delay=1, max_delay=60):
    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
    return delay

def retry_with_backoff(max_retries=3, base_delay=1, max_delay=60):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = exponential_backoff(attempt, base_delay, max_delay)
                    logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f} seconds.")
                    await asyncio.sleep(delay)
            raise Exception("Max retries exceeded")
        return wrapper
    return decorator