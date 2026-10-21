import os , subprocess  
from urllib.parse import quote





def find_app(target):
    target = target.lower()
    for folder in ["/usr/share/applications", "/var/lib/snapd/desktop/applications"]:
        if not os.path.exists(folder):
            continue
        for file in os.listdir(folder):
            if  not file.endswith(".desktop"):
                continue 
            name = file[:-8].lower()
            if target in name :
                full_path = os.path.join(folder , file)
                with open (full_path , "r") as x :
                    for line in x :
                        if line.startswith("Exec="):
                            exec_comm = line.replace("Exec=","").strip()
                            exec_comm = exec_comm.split("%")[0].strip()
                            return exec_comm



    return None



def find_folder_location(location_name):
    home = os.path.expanduser("~")
    folders={

    "desktop" : "Desktop",
    "documents" : "Documents" , 
    "downloads" : "Downloads",
    "videos" : "Videos",
    "pictures" : "Pictures",
    "music"   : "Music"

    }
    location_name = location_name.lower()
    if location_name in folders :
        path = os.path.join(home,folders[location_name])
        if os.path.isdir(path):
            return path

    return None



    
def find_path(name , kind):
    name = name.lower()
    home = os.path.expanduser("~")
    for root , dirs , files in os.walk(home):
        items = dirs if kind == "folder" else files
        for item in items :
            if name in item.lower():
                return os.path.join(root,item)

    return None 


def open_item(kind, name):
    try :
        if kind =="app" :
            comm = find_app(name)
            if comm is None :
                return {"status" : "error" , "message" : f"{name} not found"}
            subprocess.Popen(comm.split())

        elif kind == "folder" :
            path = find_folder_location(name) 
            if path is None :
                 path = find_path(name ,"folder")
            if path is None :
                return {"status" : "error"   , "message" : f"folder {name} not found"}
            subprocess.Popen(["xdg-open" , path])

        elif kind == "file":
            path = find_path(name,"file")
            if path is None :
                return {"status" : "error" , "message" : f"file {name} not found"}
            subprocess.Popen(["xdg-open" , path])

        else :
            return {"status" : "error" , "message" : f"unknown type : {kind}"}
        return {"status" : "success" , "message" : f"{kind} {name} opened"} 

    except Exception as x :

        return {"status" : "error"   ,"message" : str(x)}



# c = open_item("app" , "firefox")
# print(c)            

# c = open_item("folder" , "kok")

# print(c)          

# c= open_item("file" , "z.txt")
# print(c)


def close_item(kind , name ):
    try :
        if kind == "app" :
            f = subprocess.run(["pkill" , name] , capture_output=True , text=True)
            return {"status" : "success" , "message" : f"App {name} closed"}

        # elif kind == "folder" or kind == "file" :
        #     if kind == "folder" :
        #         path = find_folder_location(name)
        #         if path is None :
        #             path = find_path(name , "folder")
        #     else :
        #         path = find_path(name , "file")

        #     if path is None :
        #         title = name
        #     else :
        #         title = os.path.basename(path)
        #     f = subprocess.run(["wmctrl" , "-c" , title] , capture_output=True , text=True)

        # else :
        #     return {"status" : "error" , "message" : f"unknown type {kind}"}

        # if f.returncode != 0 :
        #     return {"status" : "error" , "message" : f"could not close {kind} {name}"}

        # return {"status" : "success" , "message" : f"{kind} {name} closed"}

    except Exception as x :
        return {"status" : "error" , "message" : str(x)}

    
c = close_item("app" , "firefox")
print(c)


# c = close_item("folder" , "kok")

# print(c)          

# c= close_item("file" , "z.txt")
# print(c)
# # 
    

    


def open_url(url):
    try :
        if not (url.startswith("http://") or url.startswith("https://")) :
            return {"status" : "error" , "message" : "invalid url"}
        subprocess.Popen(["xdg-open" , url])
        return {"status" : "success" , "message" : f"{url} opened"}
    except Exception as x :
        return {"status" : "error" , "message" : str(x)}


def google_search(text):
    return open_url("https://www.google.com/search?q=" + quote(text))

# c = google_search("facebook")
# print(c)


def lock_screen():
    try : 
        subprocess.run(["loginctl" , "lock-session"])
        return {"status" : "success" , "message" : "screen locked"}
    except Exception as x :
        return {"status"   : "error"    ,"message" : str(x)}

# c = lock_screen()
# print(c)





def restart_system():
    try :
        subprocess.run(["systemctl" , "reboot"])
        return {"status" : "success" , "message" : "restarting"}
    except Exception as x :
        return {"status" : "error" , "message" : str(x)}



# c = restart_system()
# print(c)




def shutdown_system():
    try :
        subprocess.run(["systemctl" , "poweroff"])
        return {"status" : "success" , "message" : "shutting down"}
    except Exception as x :
        return {"status" : "error" , "message" : str(x)}


# c = shutdown_system()
# print(c)




def set_level(kind , level):
    try :
        level = int(level)

        if kind == "brightness" :
            level = max(1 , min(100 , level))
            f = subprocess.run(["brightnessctl" , "set" , f"{level}%"] , capture_output=True , text=True)

        elif kind == "volume" :
            level = max(0 , min(100 , level))
            f = subprocess.run(["pactl" , "set-sink-volume" , "@DEFAULT_SINK@" , f"{level}%"] , capture_output=True , text=True)

        else :
            return {"status" : "error" , "message" : f"unknown type : {kind}"}

        if f.returncode != 0 :
            return {"status" : "error" , "message" : f"failed to set {kind} to {level}%"}

        return {"status" : "success" , "message" : f"{kind} set to {level}%"}

    except Exception as x :
        return {"status" : "error" , "message" : str(x)}






def mute_volume():
    try :
        check = subprocess.run(["pactl" , "get-sink-mute" , "@DEFAULT_SINK@"], capture_output=True, text=True)
        subprocess.run(["pactl" , "set-sink-mute" , "@DEFAULT_SINK@" , "toggle"])
        if "yes" in check.stdout :
            return {"status" : "success" , "message" : "volume unmuted"}
        else :
            return {"status" : "success" , "message" : "volume muted"}
    except Exception as x :
        return {"status" : "error" , "message" : str(x)}


def restart_app(target):
    try :
        close_item("app" , target)

        return open_item("app" , target)
    except Exception as x :
        return {"status" : "error" , "message" : str(x)}




def create_folder(name,locaation_name):
    try :
        location = find_folder_location(locaation_name)
        if location is None :
            return {"status" : "error"  ,   "message"  : "location not found"}
        path = os.path.join(location,name)
        os.mkdir(path)
        return {"status"   :  "success"   , "message"   :  f"folder {name} created in {location}"}
    except Exception as x :
        return {"status"   : "error"   , "message"   : str(x)}


# c = create_folder("lm","Videos")
# print(c)


def create_file(name,location_name):
    try : 
        folder = find_folder_location(location_name)
        if folder is None :
            folder = find_path(location_name,"folder")
        if folder is None :
            return {"status" :  "error" , "message"  : f"folder {location_name} not found"}
        path  = os.path.join(folder , os.path.basename(name))
        f = open(path , "x")
        f.close()
        return {"status"   :  "success"   , "message"   : f"file {name} created in {folder} "}    
    except FileExistsError :
        return {"status" : "error" , "message" : f"file {name} already exists"}
    except Exception as x :
        return {"status" : "error" , "message" : str(x)}    


c  =  create_file("ahmed" , "Music")
print(c)    