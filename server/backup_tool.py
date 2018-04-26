# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import os
import time
import io
import logging
import subprocess
import json
import ConfigParser


def write_fatal_startup(message):
    fatal_error_filename = u'error.log'
    fatal_error_filename = os.path.join(os.getcwd().decode('utf8'),
                                        fatal_error_filename)
    if len(sys.argv) == 1:
        with open(fatal_error_filename, 'w') as fatal_error_log:
            fatal_error_log.write(message)
            quit(-1)


def remove_fatal_startup():
    fatal_error_filename = u'error.log'
    fatal_error_filename = os.path.join(os.getcwd().decode('utf8'),
                                        fatal_error_filename)
    if os.path.exists(fatal_error_filename):
        os.remove(fatal_error_filename)


def make_sha512(archived_file):
    command = ['sha512sum', str(archived_file)]
    try:
        res = subprocess.check_output(command)
        return res.rstrip().split()
    except subprocess.CalledProcessError as cpe:
        logging.error('Target : %s hash calculation error. Cmd: %s, %s',
                      str(archived_file), str(cpe.cmd), str(cpe.output))
        return None


def save_dict_to_json(file_name, metadata):
    with io.open(file_name, 'w', encoding='utf8') as json_file:
        json_string = json.dumps(metadata, ensure_ascii=False)
        json_file.write(json_string.decode('utf8'))


def main(config_file):
    if config_file is None or not os.path.exists(config_file):
        print('Config file not found. Exiting.')
        quit(-1)

    cfg_parser = ConfigParser.SafeConfigParser()
    cfg_parser.read(config_file)

    if cfg_parser.has_section('log'):
        log_path = cfg_parser.get('log', 'path').decode('utf8')
        log_file_name_template = cfg_parser.get('log', 'file_name_template')
        filename_timestamp = cfg_parser.get('log', 'name_time_format')

        current_log = time.strftime(filename_timestamp, time.localtime()) + '.log'
        current_log = log_file_name_template + current_log
        current_log = os.path.join(log_path, current_log.decode('utf8'))

        log_message_format = cfg_parser.get('log', 'message_format')
        log_date_format = cfg_parser.get('log', 'time_format')

        logging.basicConfig(filename=current_log,
                            filemode='w',
                            level=logging.DEBUG,
                            format=log_message_format,
                            datefmt=log_date_format)
    else:
        print('Invalid config file. Exiting.')
        quit(-1)

    remove_fatal_startup()

    income_backup_filename = u''
    archive_list_depth = 3
    root_path = u''
    if cfg_parser.has_section('target'):
        income_backup_filename = cfg_parser.get('target', 'input_list_file').decode('utf8')
        archive_list_depth = int(cfg_parser.get('target', 'depth'))
        root_path = cfg_parser.get('target', 'path').decode('utf8')
        income_backup_filename = os.path.join(root_path,
                                              income_backup_filename)
    else:
        logging.error('Invalid config file. Exiting.')
        quit(-1)

    logging.info('Start archive update with depth %s.',
                 str(archive_list_depth))

    logging.info('Read newly added files from %s.',
                 str(income_backup_filename))

    income_backup_list = []
    with io.open(income_backup_filename, 'r', encoding='utf8') as inc_f:
        income_backup_list = inc_f.readlines()

    if income_backup_list is None or len(income_backup_list) == 0:
        logging.info('No new backup files found. Finished.')
        logging.shutdown()
        quit(0)

    income_backup_list = [f.rstrip() for f in income_backup_list]
    logging.info('Found %s new backup file(s)', str(len(income_backup_list)))

    in_metadata_dict = {}
    for el in income_backup_list:
        basic_name = el
        basic_name = basic_name[:basic_name.index(u'-')]
        zip_file_name = os.path.join(root_path, el)
        checksum_file_name = zip_file_name.replace(u'.tar.7z', u'.sha512')
        in_metadata_dict[basic_name] = [zip_file_name, checksum_file_name]

    logging.info('Start to check archive hashes.')

    for el in in_metadata_dict.keys():
        if not os.path.exists(in_metadata_dict[el][0]):
            logging.error('Archive file: %s found in %s, but not found in %s',
                          str(in_metadata_dict[el][0]),
                          str(u'backup.lst'),
                          str(root_path))
            in_metadata_dict.pop(el)
            continue

        # hash check
        archive_hash = make_sha512(in_metadata_dict[el][0])

        if archive_hash is None:
            logging.error('Can not get sha-512 for %s.',
                          str(in_metadata_dict[el][0]))

        archive_hash = archive_hash[0]

        with io.open(in_metadata_dict[el][1], 'r', encoding='utf8') as file_:
            stored_hash_str = file_.read().decode('utf8')

        if stored_hash_str is None or len(stored_hash_str) == 0:
            logging.error('Can not read stored sha-512 for %s from %s.',
                          str(in_metadata_dict[el][0]),
                          str(in_metadata_dict[el][1]))
            in_metadata_dict.pop(el)
            continue

        stored_hash_str = stored_hash_str.split()[0]
        if stored_hash_str is None or len(stored_hash_str) == 0:
            logging.error('Can not read stored sha-512 for %s from %s.',
                          str(in_metadata_dict[el][0]),
                          str(in_metadata_dict[el][1]))
            in_metadata_dict.pop(el)
            continue

        if archive_hash != stored_hash_str:
            logging.error('Checksum verification FAILED for %s. Archive removed.',
                          str(in_metadata_dict[el][0]))
            try:
                os.remove(in_metadata_dict[el][0])
                os.remove(in_metadata_dict[el][1])
            except OSError:
                logging.error('Failed archive removed for: %s and %s',
                              str(in_metadata_dict[el][0]),
                              str(in_metadata_dict[el][1]))
            in_metadata_dict.pop(el)
            continue

        logging.info('Checksum for %s verified successfully.',
                     str(in_metadata_dict[el][0]))

    logging.info('Archive checksum verification finished.')

    stored_archive_list_filename = u'stored_archives.json'
    stored_archive_list_filename = os.path.join(root_path,
                                                stored_archive_list_filename)

    archive_dict = {}
    if not os.path.exists(stored_archive_list_filename):
        logging.warning('Archive list does not exist, create the empty one: %s.',
                        stored_archive_list_filename)
        save_dict_to_json(stored_archive_list_filename, archive_dict)

    with io.open(stored_archive_list_filename, 'r', encoding='utf8') as file_:
        json_str = file_.read()
        archive_dict = json.loads(json_str)

    logging.info('Loaded archive list.')

    # merge archive list and newly added
    for basic_name in in_metadata_dict.keys():
        if basic_name not in archive_dict.keys():
            archive_dict[basic_name] = []

        archive_dict[basic_name].append(in_metadata_dict[basic_name][0])
        if len(archive_dict[basic_name]) > archive_list_depth:
            logging.info('For item: %s found more than %s archived versions. Remove the oldest one: %s.',
                         str(basic_name), str(archive_list_depth),
                         str(archive_dict[basic_name][0]))
            try:
                os.remove(archive_dict[basic_name][0])
                hash_file_name = archive_dict[basic_name][0]
                hash_file_name = hash_file_name.replace(u'.tar.7z', u'.sha512')
                os.remove(hash_file_name)
                logging.info('Deleted files: %s and %s.',
                             str(archive_dict[basic_name][0]),
                             str(hash_file_name))
            except OSError:
                logging.error('Error while delete file: %s or its hash',
                              str(archive_dict[basic_name][0]))
            finally:
                archive_dict[basic_name].remove(archive_dict[basic_name][0])

    logging.info('Archive list update finished.')

    save_dict_to_json(stored_archive_list_filename, archive_dict)
    logging.info('Archive list saved.')

    try:
        os.remove(income_backup_filename)
        logging.info('Backup list deleted: %s.',
                     str(income_backup_filename))
    except OSError:
        logging.error('Error while delete backup list: %s.',
                      str(income_backup_filename))

    logging.info('Archive update finished.')
    logging.shutdown()


if __name__ == '__main__':
    main(sys.argv[1])
