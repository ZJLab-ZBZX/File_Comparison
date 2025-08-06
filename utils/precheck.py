import os

def find_files(version_dir):
    debug_dir = ""
    images_dir = ""
    with os.scandir(version_dir) as entries:
        for entry in entries:
            if entry.is_dir() and entry.name == "debug":
                debug_dir = entry.path
            if entry.is_dir() and entry.name == "figures":
                images_dir = entry.path
    if debug_dir =="" or images_dir =="":
        raise RuntimeError(f"文件夹不完整{version_dir}")
    return debug_dir,images_dir
