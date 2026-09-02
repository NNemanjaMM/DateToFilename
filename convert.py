import os
import shutil

try:
    import pillow_heif                                    # pip install pillow-heif
    from PIL import Image
except ImportError:
    print('\nERROR: pillow-heif / Pillow not found.')
    print('       Install them with:  pip install pillow-heif Pillow')
    exit()

pillow_heif.register_heif_opener()

DIRECTORY = 'D:\\Users\\family\\Desktop\\todo'
ORIGINALS_DIR = DIRECTORY + '\\originals'

HEIC_EXTENSIONS = {'.heic', '.heif', '.hif'}
JPG_EXTENSION = '.jpg'
JPEG_QUALITY = 95
STATUS_LINE_LENGTH = 50

converted = {}
not_converted = {}

def print_status(message, current, total):
    print('  ' + message + '... |', end='')
    status = STATUS_LINE_LENGTH * current / total
    for count in range(STATUS_LINE_LENGTH):
        if count < status:
            print('+', end='')
        else:
            print('-', end='')
    print('| (', current, ' of ', total, ')       ', end='\r', sep='')
    return

if not os.path.isdir(DIRECTORY):
    print('\nERROR: directory not found:', DIRECTORY)
    exit()

heic_files = [name for name in os.listdir(DIRECTORY)
              if os.path.isfile(DIRECTORY + '\\' + name)
              and os.path.splitext(name)[1].lower() in HEIC_EXTENSIONS]

if len(heic_files) == 0:
    print('\nNo HEIC files found in:', DIRECTORY)
    exit()

print('\nWARNING: Working in directory: ', DIRECTORY)

while True:
    user_input = input('You will convert ' + str(len(heic_files)) + ' HEIC file(s) to JPG, continue? (y/n): ')
    if user_input.lower() in ['n']:
        exit()
    elif user_input.lower() in ['y']:
        break

if not os.path.isdir(ORIGINALS_DIR):
    os.makedirs(ORIGINALS_DIR)

count = 0
for file_name in heic_files:
    count += 1
    print_status('Converting', count, len(heic_files))

    source = DIRECTORY + '\\' + file_name
    base_name = os.path.splitext(file_name)[0]
    target = DIRECTORY + '\\' + base_name + JPG_EXTENSION

    # Don't clobber an existing JPG that shares the name.
    if os.path.exists(target):
        not_converted[source] = 'target already exists: ' + target
        continue

    try:
        with Image.open(source) as image:
            exif = image.info.get('exif')
            icc_profile = image.info.get('icc_profile')
            image = image.convert('RGB')
            save_options = {'quality': JPEG_QUALITY}
            if exif:
                save_options['exif'] = exif
            if icc_profile:
                save_options['icc_profile'] = icc_profile
            image.save(target, 'JPEG', **save_options)
    except Exception as e:
        not_converted[source] = str(e)
        continue

    # Only move the original once the JPG is safely written.
    try:
        shutil.move(source, ORIGINALS_DIR + '\\' + file_name)
        converted[source] = target
    except Exception as e:
        not_converted[source] = 'converted but original not moved: ' + str(e)

print('\nConversion is finished (' + str(len(converted)) + ' of ' + str(len(heic_files)) + ')')

if len(not_converted) > 0:
    print('Following files had problems (' + str(len(not_converted)) + ' of them):')
    for key in not_converted:
        print('\t', key, '->', not_converted[key])
