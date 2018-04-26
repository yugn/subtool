
# Simple Utility Backup Tool

Helps to backup selected directories on remote server.

## Requirements

Debian - based OS both on client and server.<br>
Python 2.7.<br>
7-Zip archivator (for client only).<br>
SSH connection from client to server with key authentication.<br>
NFS shared folder on server.<br>
Server wake-on-LAN capability.<br>


## Features

### Client script

Start [backup_app.py](client/backup_app.py) manually or from cron schedule. Specify configuration file [backup.cfg](client/backup.cfg) as command line argument.<br>
Script will check each of selected directories if there were any changes since last successful backup. If changes found, it will make archive file (\*.tar.7z) of selected directory and calculate archive checksum (\*.sha512 file). These files move to backup destination folder.<br>
After processing all selected directories, client script starts server script to check hash of copied archives.

#### Implementation details
To track changes in selected directories, the script recursively compare subdirectory names and file properties (size and time of last modification) between actual and stored states. So it needs also one directory to keep files with directory state descriptions.<br>
To start checking script on server side, used bash script [ssh_cmd.sh](client/ssh_cmd.sh) with simple SSH command.


### Server script
Server script [backup_tool.py](server/backup_tool.py) normally starts automatically from client command.<br>
This script also requires valid configuration file [backup.cfg](server/backup.cfg).
Script will check SHA-512 hash for each newly copied archive.<br>
Also this script checks number of versions for each archive and removes the oldest version.<br>


## Configuration files

### Client backup.cfg

```
[targets]
list_file=<path to text file with list of selected directories, i.e. /home/user/.target_dir.txt>

[metadata]
path = <path to service directory, i.e. /home/user/.temp_backup>
dict_file_name = dict.json

[destination]
mount_point = <path to destination dir mount point, i.e. /home/user/backup_dest>
path = <full path to destination dir after mounting, i.e. /home/user/backup_dest/daily_backup>
file_name_timestamp_format=%%Y-%%m-%%d
list_file_name_template=backup.lst

[server]
ip=<server ip address, i.e. 192.168.0.100>
mac=<server mac address, i.e. 00:11:22:33:44:55>

[log]
path=<path to store log of client's script, i.e. /var/log>
name_time_format=%%Y-%%m-%%dT%%H-%%M
file_name_template = backup-
message_format = %%(asctime)s %%(levelname)s %%(message)s
time_format = %%I:%%M:%%S %%p
```

Selected directories list example:
```
/home/user/Music
/home/user/Pictures
```

### Server backup.cfg

```
[log]
path=<path to store log of client's script, i.e. /var/log>
name_time_format=%%Y-%%m-%%dT%%H-%%M
file_name_template = check-
message_format = %%(asctime)s %%(levelname)s %%(message)s
time_format = %%I:%%M:%%S %%p

[target]
path=<path where script will search for new archive files, i.e. /storage/backup_hdd/backup_folder/>
depth=3
input_list_file=backup.lst
```
