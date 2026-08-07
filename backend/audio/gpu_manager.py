import asyncio

_GPU_SEMAPHORE: asyncio.Semaphore | None = None


from core.config import get_settings

def get_gpu_semaphore() -> asyncio.Semaphore:
    global _GPU_SEMAPHORE
    if _GPU_SEMAPHORE is None:
        settings = get_settings()
        _GPU_SEMAPHORE = asyncio.Semaphore(settings.gpu_concurrency)
    return _GPU_SEMAPHORE
