
def recording_func():

    return "record.wav"

def text_func(audiofile):

    return "anything"

def ai_func(text):

    return {"action":"delet",
            "target":"folder",
            "name":"folder's name"
    }

def validation_func(json_data):

    return json_data

def security_func(json_data):

    if json_data["action"]=="delet":
            return "confirm"
    
    else:
        return "approved"

def executer_func(json_data):
    
    return "command executed"
