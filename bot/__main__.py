# ...
if __name__ == '__main__':
    # Setup clean logging
    logging.basicConfig(
        format='[%(asctime)s] [%(levelname)s] - %(message)s',
        datefmt='%d-%b-%y %I:%M:%S %p',
        level=logging.INFO,
        # Add a FileHandler to also write logs to a file
        handlers=[
            logging.FileHandler("log.txt"),
            logging.StreamHandler()
        ]
    )
# ...
