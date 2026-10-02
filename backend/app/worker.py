"""CLI Entrypoint for the TrackMeld Background Planning Worker.

Usage:
    python -m backend.app.worker
"""

import sys
import asyncio
import signal
import logging

from backend.app.services.planning_worker import PlanningRunWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("trackmeld.worker.main")


async def main() -> None:
    worker = PlanningRunWorker()
    loop = asyncio.get_running_loop()

    # Graceful shutdown handler
    def handle_exit():
        logger.info("Termination signal received. Requesting worker shutdown...")
        worker.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_exit)
        except NotImplementedError:
            # Windows does not support add_signal_handler for all signals
            pass

    try:
        await worker.start()
    except (KeyboardInterrupt, SystemExit):
        worker.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker terminated by user.")
        sys.exit(0)
