import os

def find_files(version_dir):
    md_file = ""
    images_dir = ""
    with os.scandir(version_dir) as entries:
        for entry in entries:
            if entry.is_file() and entry.name == os.path.basename(version_dir)+".md":
                md_file = entry.path
            if entry.is_dir() and entry.name == "figures":
                images_dir = entry.path
    if md_file != "" and images_dir != "":
        return md_file,images_dir
    else:
        raise FileNotFoundError(f"文件夹下文件不完整，{version_dir}")
