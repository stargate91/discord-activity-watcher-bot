import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name="ActivityBot", log_file="activity_bot.log", level=logging.INFO):
    # This part sets up the bot's 'notebook' where it writes down everything it does
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # If the log file gets too big (5MB), the bot starts a new one so it doesn't take up too much space
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    handler.setFormatter(formatter)

    # This part also shows the same messages in the black command window (terminal)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.addHandler(console_handler)

    return logger

# Create the main logger that the rest of the bot will use
log = setup_logger()
