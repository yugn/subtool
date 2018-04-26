import subprocess
import os
import logging
import io
import shutil

def make_tar(source_dir, tar_file):
    command = ['tar', '-cvf', str(tar_file), str(source_dir)]
    return subprocess.call(command) == 0

def make_7z(tar_file, archived_file):
    command = ['7z', 'a', '-mx=7', str(archived_file), str(tar_file)]
    return subprocess.call(command) == 0


def make_sha512(archived_file):
    command = ['sha512sum', str(archived_file)]
    try:
        res = subprocess.check_output(command)
        return res.rstrip().split()
    except subprocess.CalledProcessError as cpe:
        logging.error('Target : %s hash calculation error. Cmd: %s, %s', str(archived_file), str(cpe.cmd), str(cpe.output))
        return None

def make_archived_file(source_dir, temp_dir, name_suffix=None):
    head, tail = os.path.split(source_dir)
    if not name_suffix is None:
        tail += name_suffix
    tar_filename = os.path.join(temp_dir, tail + '.tar')
    zipped_filename = os.path.join(temp_dir, tail + '.tar.7z')
    sha_filename = os.path.join(temp_dir, tail + '.sha512')

    if not make_tar(source_dir, tar_filename):
        logging.error('Target : %s tar error', str(source_dir))
        return [None, None, None]

    if not make_7z(tar_filename, zipped_filename):
        logging.error('Target : %s zip error', str(tar_filename))
        return [None, None, None]

    res = make_sha512(zipped_filename)

    if not res is None:
        with io.open(sha_filename, 'w', encoding='utf8') as sha_file:
            sha_file.write(' '.join(res).decode('utf8'))
        res[0] = sha_filename

    os.remove(tar_filename)

    return res

def mount_nfs_folder(path_to_mount):
    command = ['mount', str(path_to_mount)]
    try:
        res = subprocess.check_output(command)
        return True
    except subprocess.CalledProcessError as cpe:
        logging.error('Path : %s mount error. Cmd: %s, %s',
                      str(path_to_mount),
                      str(cpe.cmd),
                      str(cpe.output))
        return False

def umount_nfs_folder(path_to_umount):
    command = ['umount', str(path_to_umount)]
    try:
        res = subprocess.check_output(command)
        return True
    except subprocess.CalledProcessError as cpe:
        logging.error('Path : %s umount error. Cmd: %s, %s',
                      str(path_to_umount),
                      str(cpe.cmd),
                      str(cpe.output))
        return False

def copy_with_cleanup(src, dest_path):
    try:
        _, tail = os.path.split(src)
        shutil.copyfile(src, os.path.join(dest_path, tail))
    except:
        logging.error('Copy %s error occure.', str(src))
    finally:
        os.remove(src)

def try_execute_command(cmd):
    try:
        res = subprocess.check_output(cmd)
        return True
    except subprocess.CalledProcessError as cpe:
        logging.error('Command error: %s > %s',
                      str(cmd),
                      str(cpe.cmd) + str(cpe.output))
        return False
