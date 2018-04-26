# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import dirtool


def do_backup(path_to_cfg):
    bc = dirtool.BackupController(path_to_cfg)
    bc.backup()


if __name__ == '__main__':
    do_backup(sys.argv[1])
