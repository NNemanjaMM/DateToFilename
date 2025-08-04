import os
import time
import PIL.Image        #pip install image
from subprocess import check_output
                        #download efix tool from https://exiftool.org/

DIRECTORY = '----'
PATH_TO_EFIX_TOOL = '----'

TIME_PRINT_FORMAT = '%Y%m%d_%H%M%S'
#TIME_PRINT_FORMAT = '%Y-%m-%d %H:%M:%S'
TIME_CAPTURE_FORMAT = '%Y:%m:%d %H:%M:%S'
VIDEO_EXTENSIONS = ['.mp4', '.mov']
VIDEO_CREATION_TAG_1 = 'Create Date'
VIDEO_CREATION_TAG_2 = 'Creation Date '
VIDEO_CREATION_TAG_3 = 'File Modification Date/Time'
NAME_PREFIX = 'IMG_'

TAG_DATETIME = 306
TAG_DATETIME_ORIGINAL = 36867    # only this is used
TAG_DATETIME_DIGITIZED = 36868
STATUS_LINE_LENGTH = 50

duplication_number = 0
renaming_dictionary = {}
not_renamed = {}

def print_status(message, current, total):
    print('  ' + message + '... |', end = '')
    status = STATUS_LINE_LENGTH*current/total
    for count in range(STATUS_LINE_LENGTH):
        if count < status:
            print('+', end = '')
        else:
            print('-', end = '')
    print('| (', current, ' of ', total,')       ', end='\r', sep='')
    return

def get_duplication_index():
    global duplication_number
    duplication_number += 1
    if duplication_number < 10:
        return '_00' + str(duplication_number)
    elif duplication_number < 100:
        return '_0' + str(duplication_number)
    else:
        return '_' + str(duplication_number)

def is_video_file(filename):
    for extension in VIDEO_EXTENSIONS:
        if filename.lower().endswith(extension):
            return True
    return False

# Returns earliest 'Media creation date' metadata from video file in time format or File modification time (if earlier)
def get_date_from_video_file(filename):
    try:
        metadata_list_raw = check_output([PATH_TO_EFIX_TOOL,filename])
        metadata_list_decoded = metadata_list_raw.decode("utf-8")
        metadata_list = metadata_list_decoded.splitlines()
    except:
        time_modification = time.localtime(os.path.getmtime(filename))
        return time_modification
        
    raw_creation_date_string_1 = next((s for s in metadata_list if VIDEO_CREATION_TAG_1 in s), None)
    raw_creation_date_string_2 = next((s for s in metadata_list if VIDEO_CREATION_TAG_2 in s), None)
    time_modification = time.localtime(os.path.getmtime(filename))

    if raw_creation_date_string_1 is None and raw_creation_date_string_2 is None:
        return time_modification
    
    creation_date_time_1 = time.gmtime()
    creation_date_time_2 = time.gmtime()
    final_creation_time = time.gmtime()

    if raw_creation_date_string_1 is not None:
        reduced_creation_date_string_1 = ' '.join(raw_creation_date_string_1.split())
        final_creation_date_string_1 = reduced_creation_date_string_1.replace(VIDEO_CREATION_TAG_1 + ' : ', '')

        if final_creation_date_string_1 != '0000:00:00 00:00:00':
            creation_date_time_1 = time.strptime(final_creation_date_string_1, TIME_CAPTURE_FORMAT)

    if raw_creation_date_string_2 is not None:
        reduced_creation_date_string_2 = ' '.join(raw_creation_date_string_2.split())
        processing_creation_date_string_2 = reduced_creation_date_string_2.replace(VIDEO_CREATION_TAG_2 + ': ', '')
        final_creation_date_string_2 = processing_creation_date_string_2.split('+', 1)[0]

        if final_creation_date_string_2 != '0000:00:00 00:00:00':
            creation_date_time_2 = time.strptime(final_creation_date_string_2, TIME_CAPTURE_FORMAT)

    if creation_date_time_1 < creation_date_time_2: #Checking which metadata time is earlier
        final_creation_time = creation_date_time_1
    else:
        final_creation_time = creation_date_time_2

    if time_modification < final_creation_time: #Checking earlier metadata with file modification time
        final_creation_time = time_modification

    return final_creation_time

files_list = os.listdir(DIRECTORY)
count = 0

print('\nWARNING: Working in directory: ', DIRECTORY)

for file_name in files_list:
    count += 1  
    print_status('Collecting', count, len(files_list))


    file = DIRECTORY+'\\'+file_name 
    
    time_creation = time.localtime(os.path.getctime(file))     # usually represents a time when file is copied, so it is useless
    time_modification = time.localtime(os.path.getmtime(file))
    
    time_now = time.localtime()
    time_capture = time_now    # empty value, in case it is not obtained

    if is_video_file(file_name):
        time_capture = get_date_from_video_file(file)
    else:
        try:
            with PIL.Image.open(file) as img:
                exif_data = img._getexif()

                if exif_data:
                    if TAG_DATETIME_ORIGINAL in exif_data:
                        time_capture_string = exif_data[TAG_DATETIME_ORIGINAL]
                        time_capture = time.strptime(time_capture_string, TIME_CAPTURE_FORMAT)
        except:
            pass

    final_time = ''
    time_precision = ''
    if time_now == time_capture:
        final_time = time_modification
        time_precision = '_p2'
    else:
        final_time = time_capture
        time_precision = '_p1'

    final_time_string = time.strftime(TIME_PRINT_FORMAT, final_time)
    
    proposed_name = NAME_PREFIX + final_time_string + time_precision

    extension = file_name[-4:].lower()
    proposed_file = DIRECTORY + '\\' + proposed_name + extension

    if proposed_file in renaming_dictionary.values():
        final_name = NAME_PREFIX + final_time_string + time_precision + get_duplication_index() + extension
    else:
        final_name = NAME_PREFIX + final_time_string + time_precision + extension

    #renaming_dictionary[file] = final_name
    renaming_dictionary[file] = DIRECTORY + '\\' + final_name

print()

while True:
    user_input = input('You will rename ' + str(len(renaming_dictionary)) + ' files, continue? (y/n): ')
    if user_input.lower() in ['n']:
        exit()
    elif user_input.lower() in ['y']:
        break

count = 0
for key in renaming_dictionary:
    count += 1
    print_status('Renaming', count, len(renaming_dictionary))
    try:
        os.rename(key, renaming_dictionary[key])
    except Exception as e:
        not_renamed[key] = e.strerror

print('\nRenaming is finished')

if len(not_renamed) > 0:
    print('Following files were not renamed (' + str(len(not_renamed)) +' of them):')

for key in not_renamed:
    print('\t', key, '->', not_renamed[key])
