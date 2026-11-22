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



c = open_item("app" , "firefox")
print(c)           
c = open_item("folder" , "kok")
print(c)         
c= open_item("file" , "z.txt")
print(c)


def close_item(kind , name ):
    try :
        if kind != "app" :
            return {"status" : "error" , "message" : f"unknown type : {kind}"}

        f = subprocess.run(["pkill" , name] , capture_output=True , text=True)
        if f.returncode != 0 :
            return {"status" : "error" , "message" : f"{name} is not running"}

        return {"status" : "success" , "message" : f"App {name} closed"}

    except Exception as x :
        return {"status" : "error" , "message" : str(x)}

    
# c = close_item("app" , "firefox")
# print(c)



    


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


# c  =  create_file("ahmed" , "Music")
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

# c = set_level("volume","200")
# print(c)

# c = set_level("brightness","70")
# print(c)


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


# c = mute_volume()
# print(c)



def restart_app(target):
    try :
        close_item("app" , target)

        return open_item("app" , target)
    except Exception as x :
        return {"status" : "error" , "message" : str(x)}



# c = restart_app("firefox")
# print(c) 


def find_file(name):
    h = os.path.expanduser("~")
    for root , dirs , files  in os.walk(h):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        if name in files :
            return os.path.join(root,name)

    return None


def rename_file(old_name,new_name):
    try :
        path = find_file(old_name)
        if path is None :
            return {"status"  : "error"   , "message"   :   f"file {old_name} not found"}

        path_1 = os.path.join(os.path.dirname(path),os.path.basename(new_name))
        if os.path.exists(path_1):
            return {"status" : "error" , "message" : f"{new_name} already exists"}

        os.rename(path,path_1)
        return {"status" : "success" , "message" : f"{old_name} renamed to {new_name}"}
    except Exception as x :
        return {"status" : "error" , "message" : str(x)}

    
# c = rename_file("rizk", "ahmed")
# print(c)

        

def delete_file(name):
    try : 
        path = find_file(name)
        if path is None :
            return {"status"  :  "error"   ,  "message"  : f"file {name} not found"}

        f = subprocess.run(["gio"  , "trash"  ,path ] ,capture_output=True,text=True)
        if f.returncode != 0 :
            return {"status" : "error" , "message" : f"could not delete {name}"}

        return {"status" : "success" ,  "message" : f"file {name} moved to trash"}

    except Exception as x : 
        return {"status"  : "error"  , "message"  : str(x)}

# c = delete_file("shahin.txt")
# print(c)   


def find_folder(name):
    h   =os.path.expanduser("~")
    for root , dirs,files in os.walk(h):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        if name in dirs :
            return os.path.join(root , name )

    return None

def delete_folder(name) :
    try :
        if find_folder_location(name) is not None :
            return {"status" : "error" , "message" : f"{name} is a protected folder"}

        path = find_folder(name)
        if path is None :
            return {"status" : "error" , "message" : f"folder {name} not found"}

        f = subprocess.run(["gio" , "trash" , path] , capture_output=True , text=True)
        if f.returncode != 0 :
            return {"status" : "error" , "message" : f"could not delete {name}"}

        return {"status" : "success" , "message" : f"folder {name} moved to trash"}

    except Exception as x :
        return {"status" : "error" , "message" : str(x)}  


# c = delete_folder("lkl")
# print(c)



def list_files(location_name):
    try :
        path = find_folder_location(location_name)
        if path is None :
            path = find_path(location_name , "folder")
        if path is None :
            return {"status" : "error" , "message" : f"folder {location_name} not found"}

        items = sorted(os.listdir(path))
        if not items :
            return {"status" : "success" , "message" : f"{location_name} is empty"}

        text = ", ".join(items[:50])
        if len(items) > 50 :
            text += f" ... (+{len(items) - 50} more)"
        return {"status" : "success" , "message" : f"{len(items)} items in {location_name}: {text}"}
    except Exception as x :
        return {"status" : "error" , "message" : str(x)}



# c=list_files("Downloads")
# print(c)



def show_processes():
    try :
        f = subprocess.run(["ps" , "-eo" , "pid,comm,%cpu,%mem" , "--sort=-%cpu"] , capture_output=True , text=True)
        if f.returncode != 0 :
            return {"status" : "error" , "message" : "could not read processes"}
        lines = f.stdout.strip().split("\n")[:11]
        return {"status" : "success" , "message" : "\n".join(lines)}
    except Exception as x :
        return {"status" : "error" , "message" : str(x)}



# c = show_processes()
# print(c)


def show_usage(kind):
    try :
        msg = None

        if kind == "cpu" :
            f = subprocess.run(["vmstat" , "1" , "2"] , capture_output=True , text=True)
            lines = f.stdout.strip().split("\n")
            header = lines[1].split()
            values = lines[-1].split()
            idle = int(values[header.index("id")])
            msg = f"CPU usage: {100 - idle}%"

        elif kind == "ram" :
            f = subprocess.run(["free" , "-m"] , capture_output=True , text=True)
            for line in f.stdout.split("\n") :
                if line.startswith("Mem:") :
                    parts = line.split()
                    total = int(parts[1])
                    used = total - int(parts[6])
                    msg = f"RAM usage: {used} MB of {total} MB ({used * 100 // total}%)"

        elif kind == "disk" :
            f = subprocess.run(["df" , "-h" , "/"] , capture_output=True , text=True)
            parts = f.stdout.strip().split("\n")[1].split()
            msg = f"Disk usage: {parts[2]} used of {parts[1]} ({parts[4]}) , {parts[3]} free"

        else :
            return {"status" : "error" , "message" : f"unknown type : {kind}"}

        if f.returncode != 0 or msg is None :
            return {"status" : "error" , "message" : f"could not read {kind} usage"}

        return {"status" : "success" , "message" : msg}

    except Exception as x :
        return {"status" : "error" , "message" : str(x)}

def show_message(text):
    try :
        subprocess.Popen(["zenity" , "--info" , "--no-markup" , "--title=Result" , "--text=" + text])
    except Exception as x :
        print(x)


# c = show_processes()
# show_message(c["message"])

# c = show_usage("ram")
# show_message(c["message"])

# c = list_files("Downloads")
# show_message(c["message"])






# ==============================================================================================================================


def run_command(cmd):
    action = str(cmd.get("action") or "").lower()
    target = str(cmd.get("target") or "").lower()
    name = cmd.get("name")
    path = cmd.get("path")
    url = cmd.get("url")
    value = cmd.get("value")

    if action == "open" : 
        if url : 
            return open_url(url)
        if not name :
            return {"status"  : "error"  , "message" : "name is required"}
        return open_item(target, name )
    if action =="close" : 
        if not name : 
            return {"status" : "error" , "message" : "name is required"}
        return close_item(target ,  name)
    if action == "search" :
        if not name :
            return {"status"  : "error"  , "message" : "name is required"}
        return google_search(name)
    if action == "lock" or action == "lock_screen" : 
        return lock_screen()
    if action == "restart"  or action == "reboot" : 
        if target == "system" :
            return restart_system()
        if target == "app" : 
            if not name :

                return {"status"  : "error"  , "message" : "name is required"}
            return restart_app(name)
        return {"status" : "error" , "message" : f"unknown type : {target}"}
    if action == "mute" :
            return mute_volume()
    
    if action == "shutdown" :
            return shutdown_system()    
    if action =="set" :
        if value is None : 
            return {"status" : "error" , "message" : "value is required"}
        return set_level(target, value)
    if action =="create" : 
        if not name or not path :
                return {"status" : "error" , "message" : "name and path (location) are required"}
        if target == "folder" :
                return create_folder(name , path)
        if target == "file" :
                return create_file(name , path)
        return {"status" : "error" , "message" : f"unknown type : {target}"}
        
    if action == "delete" or action == "remove" :
        if not name :
                return {"status" : "error" , "message" : "name is required"}
        if target == "folder" :
                return delete_folder(name)
        if target == "file" :
                return delete_file(name)
        return {"status" : "error" , "message" : f"unknown type : {target}"}
    
    if action == "rename" :
        if not name or not path :
                return {"status" : "error" , "message" : "name and path (new name) are required"}
        return rename_file(name , path)
    
    if action == "list" :
        if not name :
                return {"status" : "error" , "message" : "name (location) is required"}
        return list_files(name)
    
    if action == "show" :
        if target == "processes" :
                return show_processes()
        if target in ("cpu" , "ram" , "disk") :
                return show_usage(target)
        return {"status" : "error" , "message" : f"unknown type : {target}"}
    
    return {"status" : "error" , "message" : f"not supported: {action} {target}"}
    

def execute(command):
    try :
        result = run_command(command)
    except Exception as x :
        result = {"status" : "error" , "message" : str(x)}

    if not result :
        result = {"status" : "error" , "message" : "no result"}

    if result.get("status") == "success" :
        command["status"] = "success"
        command["message"] = result.get("message" , "")
    else :
        command["status"] = "failed"
        command["error"] = result.get("message" , "unknown error")
    return command