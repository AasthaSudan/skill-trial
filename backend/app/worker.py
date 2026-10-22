"""Run the persisted SkillTrial evaluation queue as a separate process."""
import logging
from .main import STOP, initialize, worker

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    initialize()
    STOP.clear()
    try:
        worker()
    except KeyboardInterrupt:
        STOP.set()
