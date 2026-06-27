import asyncio

_GPU_SEMAPHORE: asyncio.Semaphore | None = None

def get_gpu_semaphore() -> asyncio.Semaphore:
    global _GPU_SEMAPHORE
    if _GPU_SEMAPHORE is None:
        _GPU_SEMAPHORE = asyncio.Semaphore(1)
    return _GPU_SEMAPHORE
