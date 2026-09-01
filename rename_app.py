import os
import re
import time
import shutil
import calendar
import datetime
from subprocess import check_output
                        #download efix tool from https://exiftool.org/

DIRECTORY = '***'
PATH_TO_EFIX_TOOL = '***\\DateToFilename\\exiftool\\exiftool.exe'

TIME_PRINT_FORMAT = '%Y%m%d_%H%M%S'
#TIME_PRINT_FORMAT = '%Y-%m-%d %H:%M:%S'
TIME_CAPTURE_FORMAT = '%Y:%m:%d %H:%M:%S'
NAME_PREFIX = 'IMG_'
STATUS_LINE_LENGTH = 50

# File types exiftool is asked to read a capture time from. Anything else goes straight to P2.
MEDIA_EXTENSIONS = {
    # images
    '.jpg', '.jpeg', '.jpe', '.heic', '.heif', '.hif', '.png', '.webp', '.tif', '.tiff',
    '.dng', '.cr2', '.cr3', '.nef', '.nrw', '.arw', '.rw2', '.orf', '.raf', '.pef', '.srw', '.gpr',
    # videos
    '.mp4', '.mov', '.m4v', '.avi', '.mts', '.m2ts', '.3gp', '.3g2', '.mkv', '.webm',
    '.mpg', '.mpeg', '.wmv', '.insv', '.360', '.lrv',
}

# exiftool short (-s) tag names in priority order (most trustworthy capture time first).
# The SubSec* composites fold in the EXIF UTC-offset tags, so they give a true UTC time
# when the camera recorded one; the plain tags are the fallback (offset unknown -> assumed UTC).
CAPTURE_DATETIME_TAGS = [
    'SubSecDateTimeOriginal',   # EXIF shutter time + sub-seconds + real UTC offset (best for images)
    'DateTimeOriginal',         # EXIF shutter time - phones, action cams, cameras, RAW; also many videos
    'CreationDate',             # Apple QuickTime - videos; carries the real UTC offset
    'SubSecCreateDate',         # EXIF digitized time + sub-seconds + real UTC offset
    'CreateDate',               # EXIF digitized time (images) / QuickTime create time (videos, UTC)
    'MediaCreateDate',          # video media header (UTC)
    'TrackCreateDate',          # video track header (UTC)
    'GPSDateTime',              # satellite UTC time - reliable when present
]

# Guards against bogus header dates (e.g. the 1904 MP4 epoch) becoming a wildly wrong P1.
EARLIEST_PLAUSIBLE_YEAR = 1990
LATEST_PLAUSIBLE_YEAR = time.gmtime().tm_year + 1

# Matches a trailing UTC offset on a capture-time string: 'Z', '+02:00', '-0500', etc.
TZ_SUFFIX_REGEX = re.compile(r'(Z|[+-]\d{2}:?\d{2})$')

ADJUST_TIME = False
ADJUST_TIME_DAYS = 366
ADJUST_TIME_HOURS = -3

duplication_number = 0
renaming_dictionary = {}
not_renamed = {}
errors_list = {}

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

# Parses 'YYYY:MM:DD HH:MM:SS' with an optional sub-second fraction and an optional trailing
# UTC offset ('Z', '+HH:MM', '-HHMM'); returns a UTC time.struct_time, or None for
# missing/zero/implausible values. A value with no offset is assumed to already be in UTC.
def parse_media_datetime_to_utc(value):
    value = ' '.join(value.split())

    offset_match = TZ_SUFFIX_REGEX.search(value)
    offset_token = None
    if offset_match:
        offset_token = offset_match.group(1)
        value = value[:offset_match.start()].strip()

    if '.' in value:                                  # drop sub-second fraction (GPS / SubSec tags)
        value = value.split('.', 1)[0]

    if value.startswith('0000:00:00'):
        return None

    parsed = datetime.datetime.strptime(value, TIME_CAPTURE_FORMAT)    # may raise ValueError

    if offset_token and offset_token != 'Z':
        digits = offset_token[1:].replace(':', '')
        delta = datetime.timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
        parsed = parsed - delta if offset_token[0] == '+' else parsed + delta

    if not EARLIEST_PLAUSIBLE_YEAR <= parsed.year <= LATEST_PLAUSIBLE_YEAR:
        return None                                  # bogus header date -> let the caller fall back to P2

    return time.gmtime(calendar.timegm(parsed.timetuple()))

# Returns the most precise capture datetime (UTC struct_time) from a file's metadata, or None.
# Handles any type exiftool understands: JPEG, HEIC/HEIF, PNG, WebP, TIFF, DNG/RAW,
# MP4, MOV, AVI, MTS/M2TS, 3GP, MKV, WebM, ... Tags are consulted in CAPTURE_DATETIME_TAGS
# order (most trustworthy first), not by "earliest wins".
def get_capture_datetime(filename):
    try:
        command = [PATH_TO_EFIX_TOOL, '-s', '-fast2']
        command += ['-' + tag for tag in CAPTURE_DATETIME_TAGS]
        command.append(filename)
        metadata_lines = check_output(command).decode('utf-8', 'replace').splitlines()
    except Exception:
        return None

    tags = {}
    for line in metadata_lines:
        key, separator, value = line.partition(':')
        if separator:
            tags.setdefault(key.strip(), value.strip())    # exact tag name -> value, keep first seen

    for tag_name in CAPTURE_DATETIME_TAGS:
        if tag_name not in tags:
            continue
        try:
            captured = parse_media_datetime_to_utc(tags[tag_name])
        except ValueError as e:
            errors_list[filename] = e
            continue
        if captured is not None:
            return captured

    return None

if not (os.path.isfile(PATH_TO_EFIX_TOOL) or shutil.which(PATH_TO_EFIX_TOOL)):
    print('\nERROR: exiftool not found at:', PATH_TO_EFIX_TOOL)
    print('       Get it from https://exiftool.org/ or fix PATH_TO_EFIX_TOOL.')
    print('       Without exiftool no capture datetime can be read - every file would fall back to P2/P3.')
    exit()

if not os.path.isdir(DIRECTORY):
    print('\nERROR: directory not found:', DIRECTORY)
    exit()

files_list = [name for name in os.listdir(DIRECTORY) if os.path.isfile(DIRECTORY + '\\' + name)]
count = 0

print('\nWARNING: Working in directory: ', DIRECTORY)

for file_name in files_list:
    count += 1  
    print_status('Collecting', count, len(files_list))


    file = DIRECTORY+'\\'+file_name

    # P2 source: earliest filesystem timestamp (creation or modification), in UTC. Always preferred over "now".
    try:
        time_from_file = min(time.gmtime(os.path.getctime(file)),
                             time.gmtime(os.path.getmtime(file)))
    except OSError:
        time_from_file = None

    # P1 source: most precise capture datetime from media metadata, normalised to UTC
    time_capture = None
    if os.path.splitext(file_name)[1].lower() in MEDIA_EXTENSIONS:
        time_capture = get_capture_datetime(file)

    if time_capture is not None:
        final_time = time_capture
        time_precision = '_p1'
    elif time_from_file is not None:
        final_time = time_from_file
        time_precision = '_p2'
    else:
        final_time = time.gmtime()
        time_precision = '_p3'
     
    if ADJUST_TIME:
        time_adjust = datetime.datetime(*final_time[:6])
        time_adjust = time_adjust + datetime.timedelta(days=ADJUST_TIME_DAYS)
        time_adjust = time_adjust + datetime.timedelta(hours=ADJUST_TIME_HOURS)
        final_time_string=time_adjust.strftime(TIME_PRINT_FORMAT)
    else:
        final_time_string = time.strftime(TIME_PRINT_FORMAT, final_time)
    
    proposed_name = NAME_PREFIX + final_time_string + time_precision

    extension = os.path.splitext(file_name)[1].lower()
    proposed_file = DIRECTORY + '\\' + proposed_name + extension

    if proposed_file in renaming_dictionary.values():
        final_name = NAME_PREFIX + final_time_string + time_precision + get_duplication_index() + extension
    else:
        final_name = NAME_PREFIX + final_time_string + time_precision + extension

    #renaming_dictionary[file] = final_name
    renaming_dictionary[file] = DIRECTORY + '\\' + final_name

print()

if len(errors_list) > 0:
    print('******************************************************')
    for key in errors_list:    
        print('File: ', key, '\nError: ', errors_list[key])
        print()
    print('******************************************************')
    print('Error(s) found, still continue?')

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
