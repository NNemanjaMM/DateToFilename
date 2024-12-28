import os
import shutil

directory = 'D:\\Users\\porodični\\Desktop\\tel niki'


def move_all_files_to_destination_dir(original_dir, destination_dir, count):
    # moves all NESTED files in original_dir to destination_dir
    files = []
    for root, dirs, files in os.walk(original_dir):
        for name in files:
            os.rename(root + os.sep + name, destination_dir + os.sep + str(count) + '-' + name)
            #shutil.move()
            

count = 0 
subdirs = [f.path for f in os.scandir(directory) if f.is_dir()]   # [Folder1, Folder2]
for d in subdirs:
    move_all_files_to_destination_dir(d, directory, count)
    # remove the subdirectories of d after we have moved all files under it
    for sub in os.scandir(d):
        if sub.is_dir():
            shutil.rmtree(sub)
    count += 1