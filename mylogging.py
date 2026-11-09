import logging

def getlogger(name):

    logger = logging.getLogger(name)
    if not logger.handlers:

        logger.setLevel(logging.INFO)
        file_handler= logging.FileHandler("test.log")
        formatter= logging.Formatter("%(asctime)s  %(name)s %(levelname)s %(message)s",
                                    datefmt="%Y/%m/%d %H:%M:%S:" )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
    
logger= getlogger("Ahmed")         
logger.info("kalam kter malosh da3y ")        

