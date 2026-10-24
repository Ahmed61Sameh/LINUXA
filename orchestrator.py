from stubs_func import *
from mylogging import *

logger = getlogger("orchestrator")

def linuxa():

    try:

        audio = recording_func()
        logger.info(f"from audio file {audio}")

        text = text_func(audio)

        json_data = ai_func(text)

        validationo_data = validation_func(json_data)

        securied_data = security_func(validationo_data)

        if securied_data =="confirm":
    
            response=input("Are you sure you want to contiuno Y or N").lower()

            if response !="y":
                print("Cancelled")
                
                return 

        result = executer_func(validationo_data)

        # print(f"{audio} \n {text}\n {json_data}\n {validationo_data}\n {securied_data}\n {result}")

        logger.info("command executed")

        return result

    except Exception as e :

        logger.error(f"error {e} ")

if __name__== "__main__":

    result= linuxa()
    print(result)

