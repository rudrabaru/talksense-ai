import asyncio
import logging
import os
import struct
import sys
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import crud
from db.database import AsyncSessionLocal
from db.models import Session as DBSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger("verify_restart_recovery")


def build_dummy_wav(path: str, data_size: int):
    """Write a WAV file with 0 sizes in the header, followed by dummy data."""
    num_channels = 1
    sample_rate = 16000
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8

    # Header with placeholder 0 sizes (simulating crash)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + 0,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        0,
    )

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(header)
        # Write some dummy PCM bytes (zeros)
        f.write(b"\x00" * data_size)


def parse_wav_header(path: str):
    """Read the ChunkSize and Subchunk2Size from the WAV file."""
    with open(path, "rb") as f:
        f.seek(4)
        chunk_size = struct.unpack("<I", f.read(4))[0]
        f.seek(40)
        subchunk2_size = struct.unpack("<I", f.read(4))[0]
    return chunk_size, subchunk2_size


async def main():
    logger.info("=" * 60)
    logger.info("Starting Stale Session & WAV Recovery Test")
    logger.info("=" * 60)

    # 1. Initialize DB tables
    # await create_all()

    session_id = str(uuid.uuid4())
    logger.info(f"Created test session ID: {session_id}")

    # Create dummy unfinalized WAV file on disk
    safe_id = session_id.replace("-", "")[:16]
    wav_filename = f"session_{safe_id}.wav"
    wav_path = os.path.join("session_audio", wav_filename)
    dummy_data_size = 32000  # 1 second of audio at 16kHz 16-bit mono

    build_dummy_wav(wav_path, dummy_data_size)
    logger.info(
        f"Created unfinalized WAV at {wav_path} with size {os.path.getsize(wav_path)} bytes"  # noqa: E501
    )

    # Verify initial header placeholder sizes are indeed 0
    init_chunk, init_subchunk = parse_wav_header(wav_path)
    logger.info(
        f"Initial header values: ChunkSize={init_chunk}, Subchunk2Size={init_subchunk}"
    )
    assert init_chunk == 36, "Initial ChunkSize should be 36 (36 + 0)"
    assert init_subchunk == 0, "Initial Subchunk2Size should be 0"

    async with AsyncSessionLocal() as db:
        # 2. Seed a stale session in the database
        db_sess = DBSession(
            id=uuid.UUID(session_id),
            mode="meeting",
            status="active",
            audio_file_path=None,
        )
        db.add(db_sess)
        await db.commit()
        logger.info("Seeded stale 'active' session into database.")

        # 3. Execute recovery
        logger.info("Running recover_stale_sessions...")
        affected = await crud.recover_stale_sessions(db)
        logger.info(f"Recovery finished. Affected sessions: {affected}")
        assert affected >= 1, "Should have affected at least the test session"

        # 4. Verify DB updates
        recovered_sess = await crud.get_session(db, session_id)
        assert recovered_sess is not None
        logger.info(f"Recovered session status: '{recovered_sess.status}'")
        logger.info(f"Recovered session audio path: '{recovered_sess.audio_file_path}'")

        assert (
            recovered_sess.status == "interrupted"
        ), "Session status should be interrupted"
        assert recovered_sess.audio_file_path == os.path.abspath(
            wav_path
        ), "Audio path should be mapped"

    # 5. Verify WAV header finalization
    final_chunk, final_subchunk = parse_wav_header(wav_path)
    logger.info(
        f"Finalized header values: ChunkSize={final_chunk}, Subchunk2Size={final_subchunk}"  # noqa: E501
    )
    expected_chunk_size = 36 + dummy_data_size
    expected_subchunk_size = dummy_data_size

    assert (
        final_chunk == expected_chunk_size
    ), f"Expected ChunkSize {expected_chunk_size}, got {final_chunk}"
    assert (
        final_subchunk == expected_subchunk_size
    ), f"Expected Subchunk2Size {expected_subchunk_size}, got {final_subchunk}"

    # 6. Cleanup
    if os.path.exists(wav_path):
        os.remove(wav_path)
        logger.info("Cleaned up test WAV file.")

    async with AsyncSessionLocal() as db:
        await db.delete(recovered_sess)
        await db.commit()
        logger.info("Cleaned up database test session row.")

    logger.info("=" * 60)
    logger.info("✅ All Checks Passed Successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
