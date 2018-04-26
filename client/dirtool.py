# -*- coding: utf-8 -*-


from __future__ import print_function
import os
import sys
import hashlib
import time
import logging
import json
import io
import ConfigParser
import nettool
import systool


class DirDescriptor(object):
    """
    Descriptor for directory
    """
    def __init__(self, directory, time_string_format='%Y-%m-%dT%H:%M:%SZ%Z'):
        if not os.path.isdir(directory):
            logging.error('File reading error: {}', directory)
            raise TypeError("Directory must be a directory.")
        self.metadata = dict()
        self.metadata[u'directory'] = os.path.basename(directory.decode('utf8'))
        self.metadata[u'path'] = os.path.abspath(directory).decode('utf8')
        self.metadata[u'parent'] = os.path.dirname(self.metadata[u'path']).decode('utf8')
        self.metadata[u'hash'] = u''
        self.time_format = time_string_format

    def __relpath(self, path):
        return os.path.relpath(path, start=self.metadata[u'path'])

    def iterfiles(self):
        for root, dirs, files in os.walk(self.metadata[u'path'], topdown=True):
            for f in files:
                yield self.__relpath(os.path.join(root, f))

    def itersubdirs(self):
        for root, dirs, files in os.walk(self.metadata[u'path'], topdown=True):
            for d in dirs:
                yield self.__relpath(os.path.join(root, d))

    def files(self, sort_key=lambda k: k, sort_reverse=False):
        return sorted(self.iterfiles(), key=sort_key, reverse=sort_reverse)

    def subdirs(self, sort_key=lambda k: k, sort_reverse=False):
        return sorted(self.itersubdirs(), key=sort_key, reverse=sort_reverse)

    def load_actual_state(self):
        self.metadata[u'subdirs'] = self.subdirs()
        sha_obj = hashlib.sha512()
        sha_obj.update(self.metadata[u'directory'].encode('utf8'))
        for s in self.metadata[u'subdirs']:
            sha_obj.update(s.encode('utf8'))

        self.metadata[u'files'] = []
        for f in self.files():
            sys_info = os.stat(os.path.join(self.metadata[u'path'], f))
            str_mtime = time.strftime(self.time_format, time.gmtime(sys_info.st_mtime))
            str_size = str(sys_info.st_size)
            sha_obj.update(f.encode('utf8'))
            sha_obj.update(str_mtime)
            sha_obj.update(str_size)
            self.metadata[u'files'].append([f,
                                           str_mtime.decode('utf8'),
                                           str_size.decode('utf8')])
        self.metadata[u'hash'] = sha_obj.hexdigest().decode('utf8')

    def load_stored_state(self, json_file):
        if os.path.exists(json_file) and os.path.isfile(json_file):
            with io.open(json_file, 'r', encoding='utf8') as source_file:
                json_str = source_file.read()
                self.metadata = json.loads(json_str)
        else:
            logging.error('File %s for load Directory descriptor not found.', str(json_file))

    def save_to_json(self, filename):
        if filename is None:
            logging.warning('No file to save json object for: {}', str(self.metadata[u'directory']))
            return
        with io.open(filename, 'w', encoding='utf8') as json_file:
            json_string = json.dumps(self.metadata, ensure_ascii=False)
            json_file.write(json_string)

    def __eq__(self, other):
        return self.metadata == other.metadata

    def __ne__(self, other):
        return self.metadata != other.metadata


class BackupController(object):

    def __init__(self, config_file):

        if config_file is None or not os.path.exists(config_file):
            print('Config file not found. Exiting.')
            quit(-1)

        cfg_parser = ConfigParser.SafeConfigParser()
        cfg_parser.read(config_file)

        if cfg_parser.has_section('log'):
            self._log_path = cfg_parser.get('log', 'path').decode('utf8')
            self._log_file_name_template = cfg_parser.get('log', 'file_name_template')
            self._filename_timestamp = cfg_parser.get('log', 'name_time_format')
            self._log_message_format = cfg_parser.get('log', 'message_format')
            self._log_date_format = cfg_parser.get('log', 'time_format')
            self.__init_log_file()
            logging.info('Backup started')
        else:
            print('Invalid config file. Exiting.')
            quit(-1)

        if cfg_parser.has_section('targets'):
            self._target_list_file = cfg_parser.get('targets', 'list_file').decode('utf8')
            self._target_list = []
        else:
            logging.error('Invalid config file, %s not found. Exiting.', 'targets')
            quit(-1)

        if cfg_parser.has_section('metadata'):
            self._metadata_path = cfg_parser.get('metadata', 'path').decode('utf8')
            self._metadata_dict_file_name = cfg_parser.get('metadata', 'dict_file_name').decode('utf8')
            self._metadata_dict_file = u''
            self._metadata = {}
        else:
            logging.error('Invalid config file, %s not found. Exiting.', 'metadata')
            quit(-1)

        if cfg_parser.has_section('server'):
            self.server_ip = cfg_parser.get('server', 'ip')
            self.server_mac = cfg_parser.get('server', 'mac')
        else:
            logging.error('Invalid config file, %s not found. Exiting.', 'server')
            quit(-1)

        if cfg_parser.has_section('destination'):
            self._dest_mount = cfg_parser.get('destination', 'mount_point').decode('utf8')
            self._dest_path = cfg_parser.get('destination', 'path').decode('utf8')
            self._backup_list_filename = cfg_parser.get('destination', 'list_file_name_template').decode('utf8')
            self._backup_name_timestamp = cfg_parser.get('destination', 'file_name_timestamp_format')
        else:
            logging.error('Invalid config file, %s not found. Exiting.', 'destination')
            quit(-1)

    @property
    def log_path(self):
        return self._log_path

    @log_path.setter
    def log_path(self, value):
        if (value is not None) and len(value) > 0 and os.path.exists(value):
            self._log_path = value.decode('utf8')

    @property
    def log_file_name(self):
        current_time = time.strftime(self._filename_timestamp, time.localtime())
        log_file = self._log_file_name_template + current_time
        log_file += '.log'
        log_file = os.path.join(self._log_path, log_file.decode('utf8'))
        return log_file

    @property
    def metadata_path(self):
        return self._metadata_path

    @metadata_path.setter
    def metadata_path(self, value):
        if (value is not None) and len(value) > 0 and os.path.exists(value):
            self._metadata_path = value.decode('utf8')

    @property
    def metadata_dict_name(self):
        self._metadata_dict_file = os.path.join(self._metadata_path, self._metadata_dict_file_name)
        if not os.path.exists(self._metadata_dict_file):
            logging.warning('Metadata dictionary file not found: %s, creating new.', str(self._metadata_dict_file))
            self.__save_metadata_dict({})
        return self._metadata_dict_file

    @property
    def dest_path(self):
        return self._dest_path

    @dest_path.setter
    def dest_path(self, value):
        if (value is not None) and len(value) > 0:
            if not os.path.exists(value):
                logging.warning('Destination directory not found: %s', str(self.dest_path))
            self._dest_path = value.decode('utf8')

    @property
    def dest_mount(self):
        return self._dest_mount

    @dest_mount.setter
    def dest_mount(self, value):
        if (value is not None) and len(value) > 0:
            if os.path.exists(value):
                self._dest_mount = value.decode('utf8')
            else:
                logging.error('Destination directory mount point not found: ', self.dest_mount)

    @property
    def target_list_file(self):
        return self._target_list_file

    @target_list_file.setter
    def target_list_file(self, value):
        if (value is not None) and len(value) > 0 and os.path.exists(value):
            self._target_list_file = value.decode('utf8')

    @property
    def target_list(self):
        if len(self._target_list) == 0:
            self.__load_target_list()
        return self._target_list

    def __init_log_file(self):
        logging.basicConfig(filename=self.log_file_name,
                            filemode='w',
                            level=logging.DEBUG,
                            format=self._log_message_format,
                            datefmt=self._log_date_format)

    def __save_metadata_dict(self, metadata):
        with io.open(self._metadata_dict_file, 'w', encoding='utf8') as json_file:
            json_string = json.dumps(metadata, ensure_ascii=False)
            json_file.write(json_string.decode('utf8'))

    def __load_target_list(self):
        self._target_list = []
        with io.open(self.target_list_file, 'r', encoding='utf8') as target_file:
            self._target_list = [s.rstrip() for s in target_file.readlines() if len(s) > 1]
        if len(self._target_list) == 0:
            logging.error('List of backup directories is empty.')
            quit(-1)

    def _save_backup_list(self, file_list):
        with io.open(os.path.join(self.dest_path, self._backup_list_filename), 'w', encoding='utf8') as dest_file:
            dest_file.write(('\n'.join(file_list)).decode('utf8'))

    def load_metadata(self):

        if len(self.target_list) == 0:
            logging.error('List of backup directories is empty.')
            quit(-1)

        #  load existing metadata
        metadata_dict_file = self.metadata_dict_name
        if metadata_dict_file is None:
            quit(-1)
        metadata_dict = {}
        with io.open(metadata_dict_file, 'r', encoding='utf8') as dict_file:
            metadata_dict = json.loads(dict_file.read())

        resolved_metadata = {}
        for d in self.target_list:
            if d in metadata_dict.keys():
                resolved_metadata[d] = metadata_dict[d]
            else:
                # newly added target, no metadata exist
                resolved_metadata[d] = None

        if len(resolved_metadata) == 0:
            logging.error('Actual metadata not found.')
            quit(-1)

        # delete expired metadata files without targets
        keys_to_remove = [k for k in metadata_dict.keys() if k not in self.target_list]
        if len(keys_to_remove) > 0:
            for k in keys_to_remove:
                logging.warning('Remove metadata descriptor: %s', str(k))
                # delete metadata file
                os.remove(os.path.join(self._metadata_path, metadata_dict[k]))
        return resolved_metadata

    def backup(self):
        # check settings
        if self.target_list is None or len(self.target_list) == 0:
            logging.error('Target list empty: %s', str(self.target_list_file))
            quit(-1)
        if self.metadata_dict_name is None:
            logging.error('Metadata dictionary not found: %s.', str(self.metadata_dict_name))

        if self.dest_mount is None or len(self.dest_mount) == 0:
            logging.error('Destination mount point not found: %s', str(self.dest_mount))
            quit(-1)

        # connect network folder
        if not nettool.ping(self.server_ip, n_packets=2):
            logging.info('Server (ip=%s) wake-on-LAN start.', str(self.server_ip))
            nettool.wake_on_lan(self.server_mac)
            if not nettool.ping(self.server_ip, n_packets=2, wait_before=60):
                logging.error('Server wake-on-LAN failed: %s , %s', str(self.server_ip), str(self.server_mac))
                quit(-1)

        if not systool.mount_nfs_folder(self.dest_mount):
            logging.error('Server folder mount failed: %s', str(self.dest_mount))
            quit(-1)

        if self.dest_path is None:
            logging.error('Destination path not found: %s', str(self.dest_path))
            quit(-1)

        # load stored metadata about target directories
        actual_metadata = self.load_metadata()
        backuped_list = []

        # compare stored and actual metadata on each target dir
        for curr_target in actual_metadata.keys():
            m_el = actual_metadata[curr_target]
            logging.info('Process directory %s ...', str(curr_target))
            target_descr = DirDescriptor(curr_target)
            target_descr.load_actual_state()
            need_backup = False

            if m_el is None:
                logging.info('Create new directory description for %s ', str(curr_target))
                _, body = os.path.split(curr_target)
                actual_metadata[curr_target] = body + u'.json'
                target_descr.save_to_json(os.path.join(self.metadata_path, actual_metadata[curr_target]))
                logging.info('Description %s saved.', str(actual_metadata[curr_target]))
                need_backup = True
            else:
                control_descr = DirDescriptor(curr_target)
                control_descr.load_stored_state(os.path.join(self.metadata_path, actual_metadata[curr_target]))

                if control_descr == target_descr:
                    logging.info('Changes not found at %s ', str(curr_target))
                else:
                    logging.info('Found changes at %s ', str(curr_target))
                    need_backup = True

            # update archive for this directory
            if need_backup:
                logging.info('Creating archive for %s ', str(curr_target))
                current_time = '-' + time.strftime(self._backup_name_timestamp, time.localtime())
                res = systool.make_archived_file(curr_target, self.metadata_path, name_suffix=current_time)

                if (res is None) or len(res) != 2:
                    logging.error('Can not create archive for %s', str(curr_target))
                    continue

                # copy archive and its hash into destination dir
                systool.copy_with_cleanup(res[1], self.dest_path)
                systool.copy_with_cleanup(res[0], self.dest_path)
                logging.info('Copy %s and %s done.', str(res[1]), str(res[1]))
                _, res[1] = os.path.split(res[1])
                backuped_list.append(res[1])

        # save updated metadata
        self.__save_metadata_dict(actual_metadata)

        # save list of updated archives in destination dir
        if len(backuped_list) > 0:
            self._save_backup_list(backuped_list)
        else:
            logging.info('No changed directories found, finishing.')

        # start hash check on server side
        exec_path, _ = os.path.split(sys.argv[0])
        exec_path = os.path.join(exec_path, 'ssh_cmd.run')
        if not systool.try_execute_command(exec_path):
            logging.error('Checksum recalculation task on serverside failed: %s', str(exec_path))
        else:
            logging.info('Checksum recalculation task on serverside start: %s', str(exec_path))

        # disconnect net folders
        if not systool.umount_nfs_folder(self.dest_mount):
            logging.error('Server folder umount failed: %s', str(self.dest_mount))
        logging.info('Backup finished.')
