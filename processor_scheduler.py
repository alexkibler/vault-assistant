#!/usr/bin/env python3
"""
Scheduler for running the note processor on a recurring interval.

Runs processor.process_all_unprocessed() every PROCESSOR_INTERVAL minutes.
Designed to run continuously in a Docker container.
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime

import schedule

from processor import process_all_unprocessed

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("processor-scheduler")

# Configuration
PROCESSOR_INTERVAL = int(os.getenv("PROCESSOR_INTERVAL", "30"))  # minutes


async def run_processor():
    """Run the processor and log results."""
    logger.info("Starting processor run...")
    try:
        await process_all_unprocessed()
        logger.info("Processor run completed successfully")
    except Exception as e:
        logger.error(f"Processor run failed: {e}", exc_info=True)


def schedule_processor():
    """Schedule processor to run on interval."""
    schedule.every(PROCESSOR_INTERVAL).minutes.do(
        lambda: asyncio.run(run_processor())
    )
    logger.info(f"Processor scheduled to run every {PROCESSOR_INTERVAL} minutes")


def main():
    """Main scheduler loop."""
    logger.info("Vault Assistant Processor Scheduler starting")
    logger.info(f"Interval: {PROCESSOR_INTERVAL} minutes")

    schedule_processor()

    # Run processor immediately on startup
    logger.info("Running initial processor pass...")
    asyncio.run(run_processor())

    # Keep running and process scheduled jobs
    logger.info("Entering scheduler loop...")
    while True:
        try:
            schedule.run_pending()
            # Check every 10 seconds for pending jobs
            time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Scheduler interrupted, shutting down")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
            # Continue running even on error
            time.sleep(60)


if __name__ == "__main__":
    main()
