import argparse
import os
import piexif
import re
import time

from pywintypes import Time
from win32file import CreateFile, SetFileTime, CloseHandle
from win32file import GENERIC_READ, GENERIC_WRITE, OPEN_EXISTING


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, required=True, help="Input path.")
    parser.add_argument("--date-format", type=str, choices=['YYYYMMDD', 'YYYY-MM-DD', 'YYYYMM', 'YYYY-MM'],
                        default='YYYYMMDD',
                        help="Set the format for getting the time info from the parent directory name."
                             " Support YYYYMMDD(default), YYYY-MM-DD, YYYYMM and YYYY-MM.")
    parser.add_argument("--force", action='store_true',
                        help="Force the time information to be written into the EXIF of the JPG/JPEG file,"
                             " even if the time information already exists in the EXIF.")

    args = parser.parse_args()
    return args


def write_time(args):
    pattern_dict = {
        'YYYY-MM-DD': '^(\d{4})-(\d{2})-(\d{2})\s',
        'YYYYMMDD': '^(\d{4})(\d{2})(\d{2})\s',
        'YYYY-MM': '^(\d{4})-(\d{2})\s',
        'YYYYMM': '^(\d{4})(\d{2})\s',
    }
    pattern_date = pattern_dict[args.date_format]

    dir_list = os.listdir(args.path)
    for dir_name in dir_list:
        exif_time = '1970:01:01 00:00:00'
        file_time = '1970-01-01 00:00:00'

        if re.match(pattern_date, dir_name):
            date_tuple = re.findall(pattern_date, dir_name)[0]
            if args.date_format in ['YYYY-MM-DD', 'YYYYMMDD']:
                exif_time = date_tuple[0] + ':' + date_tuple[1] + ':' + date_tuple[2] + ' 00:00:00'
                file_time = date_tuple[0] + '-' + date_tuple[1] + '-' + date_tuple[2] + ' 00:00:00'
            elif args.date_format in ['YYYY-MM', 'YYYYMM']:
                exif_time = date_tuple[0] + ':' + date_tuple[1] + ':' + '01' + ' 00:00:00'
                file_time = date_tuple[0] + '-' + date_tuple[1] + '-' + '01' + ' 00:00:00'

            g = os.walk(args.path + '\\' + dir_name)
            for dir_path, dir_names, filenames in g:
                for filename in filenames:
                    file_full_path = os.path.join(dir_path, filename)
                    if check_format(file_full_path):
                        if args.force or not check_exif(file_full_path):
                            write_exif(file_full_path, exif_time, exif_time, exif_time)
                    else:
                        modify_file_time(file_full_path, file_time, file_time, file_time)
        else:
            print(dir_name + ' not match')


def write_exif(path, exif_date_time, exif_date_time_original, exif_date_time_digitized):
    """
    ????????????????????????????????? Exif??????????????????YYYY:MM:DD HH:MM:SS

    :param path: ?????????????????????
    :param exif_date_time: ????????????
    :param exif_date_time_original: ????????????
    :param exif_date_time_digitized: ??????????????????????????????
    :return:
    """
    try:
        # ???????????? Exif ??????
        exif_dict = piexif.load(path)
        # ?????? Exif ??????????????? DateTime ??? ImageIFD ??????
        # DateTime(0x0132): ???????????????????????????????????????/??????
        exif_dict['0th'][piexif.ImageIFD.DateTime] = exif_date_time
        # DateTimeOriginal(0x9003): ??????????????????????????????/??????
        exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = exif_date_time_original
        # DateTimeDigitized(0x9004): ??????????????????????????????/?????????????????? DateTimeOriginal(0x9003) ??????????????????
        exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = exif_date_time_digitized
        try:
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, path)  # ??????Exif??????
            print(
                f'Done, photo time has been changed to {exif_date_time}, {exif_date_time_original}, {exif_date_time_digitized}')
            return 0
        except:
            print(f'Exif dump error')
            return 1
    except:
        print('Exif load error')
        return 1


def modify_file_time(file_path, create_time, modify_time, access_time):
    """
    ?????????????????????????????????????????????YYYY-MM-DD HH:MM:SS

    :param file_path: ????????????
    :param create_time: ????????????
    :param modify_time: ????????????
    :param access_time: ????????????
    """
    try:
        date_format = "%Y-%m-%d %H:%M:%S"

        fh = CreateFile(file_path, GENERIC_READ | GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, 0)

        createTime = Time(time.mktime(time.strptime(create_time, date_format)))
        modifyTime = Time(time.mktime(time.strptime(modify_time, date_format)))
        accessTime = Time(time.mktime(time.strptime(access_time, date_format)))

        SetFileTime(fh, createTime, accessTime, modifyTime)
        CloseHandle(fh)
        print(f'Done, file time has been changed to {createTime}, {accessTime}, {modifyTime}')
        return 0
    except:
        print(f'Modify file time error')
        return 1


# ??????????????? JPG ??????
def check_format(photo_path):
    try:
        return str.upper(os.path.splitext(photo_path)[1][1:]) in ['JPG', 'JPEG']
    except:
        return False


# ?????? Exif ????????????????????????
def check_exif(photo_path):
    try:
        exif_dict = piexif.load(photo_path)  # ??????Exif??????
        return piexif.ExifIFD.DateTimeOriginal in exif_dict['Exif']
    except:
        return False


# ???????????? Exif ????????????????????????????????????
def get_exif(path):
    exif_dict = piexif.load(path)
    photo_time = exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal]  # bytes
    photo_time = bytes.decode(photo_time)  # ????????????2021:04:22 07:07:07
    return photo_time


if __name__ == '__main__':
    write_time(get_args())
