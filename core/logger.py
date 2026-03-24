import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name="ActivityBot", log_file="activity_bot.log", level=logging.INFO):
    """Function to setup as many loggers as you want"""
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Ensure the log file is in a consistent location (project root)
    # If the bot is started by the manager, cwd will be the bot's path.
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.addHandler(console_handler)

    return logger

# Initialize the global logger
log = setup_logger()
