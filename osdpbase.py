"""
Open Source Development Platform Base Class.
This module contains the base class for OSDP
(OSDPBase).

"""
import boto3
import sys
from ruamel.yaml import YAML
from git import Repo
from git import RemoteProgress
import git
import os
from pathlib import Path
import argparse
import vagrant
import json
import errno
from subprocess import check_output
import subprocess
import botocore
import zipfile
import datetime
import logging
import os.path
import shutil
import docker
import dockerpty
import socket

__author__ = "James Knott (@Ghettolabs)"
__copyright__ = "Copyright 2018 James Knott"
__credits__ = ["James Knott"]
__license__ = "Apache License, 2.0"
__version__ = "0.0.3"
__maintainer__ = "James Knott"
__email__ = "devops@ghettolabs.io"
__status__ = "Development"

def is_connected(REMOTE_SERVER):
  try:
    host = socket.gethostbyname(REMOTE_SERVER)
    s = socket.create_connection((host, 80), 2)
    print("Connected to the internet")
    return True
  except:
     pass
  return False


def setup_logging():
    logger = logging.getLogger()
    for h in logger.handlers:
      logger.removeHandler(h)
    h = logging.StreamHandler(sys.stdout)
    #FORMAT = "[%(levelname)s %(asctime)s %(filename)s:%(lineno)s - %(funcName)21s() ] %(message)s"
    FORMAT = "[%(levelname)s %(asctime)s %(filename)s:%(lineno)s - %(funcName)21s() ] %(message)s"
    h.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)
    return logger


class MyProgressPrinter(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        print(op_code, cur_count, max_count, cur_count / (max_count or 100.0), message or "Downloading....")



class OSDPBase(object):

    def __init__(self):
        self.current_directory = os.getcwd()
        self.final_directory = os.path.join(self.current_directory, r"osdp/configuration")
        self.directory = 'osdp'
        self.my_file = Path(r"osdp/keys/private.bin")
        self.secret_code = ''
        self.encoded_key = ''
        self.linux = ['ubuntu', 'centos', 'debian', 'amazon', 'dcos-vagrant', 'xenial', 'docker', 'amazonlinux', 'docker-lambda']
        self.logger = setup_logging()
        self.REMOTE_SERVER = "www.github.com"
    def init(self):
        if is_connected(self.REMOTE_SERVER):
            try:
                if not os.path.exists(self.final_directory):
                    os.makedirs(self.final_directory)
                Repo.clone_from('https://github.com/james-knott/configuration.git', self.final_directory , branch="master", progress=MyProgressPrinter())
                self.logger.info("Downloaded the settings.yml file. Go to osdp/configuration/settings.yml to customize your environment!")
            except git.exc.GitCommandError as e:
                self.logger.info("Could not clone the repo. Folder may exist.!")
                if os.path.isfile('osdp/configuration/settings.yml'):
                    self.logger.info("Found the settings.yml file. It has already been downloaded!")
                else:
                    self.logger.info("Could not connect to Github to download the settings.yml file. Creating Dynamically!")
                    inp = """\
                    # Open Source Development Platform
                    osdp:
                      # details
                      linux: amazon   # So we can develop AWS Lambda with same python version
                      username: jknott
                      project: company
                      platform: docker # Currently supported docker and vagrant
                      runtime: python3.6
                      dockerhubusername: buildmystartup
                      dockerhubpassword: mypassword
                      imagename: buildmystartup/ghettolabs
                      pushto: ghettolabs/python
                      dockerdeveloperimage: buildmystartup/ghettolabs:python3.6
                    """
                    yaml = YAML()
                    code = yaml.load(inp)
                    #yaml.dump(code, sys.stdout) test what they dynamic file looks like
                    self.logger("Your new projecct name is", code['osdp']['project'])
                    if not os.path.exists(self.final_directory):
                        os.makedirs(self.final_directory)
                    with open('osdp/configuration/settings.yml', "w") as f:
                        yaml.dump(code, f)
        else:
            print("Network connection is down")


    def new(self):
        dataMap = self.get_settings()
        current_directory = os.getcwd()
        data_folder = Path("osdp")
        if dataMap['osdp']['platform'] == 'vagrant':
            file_to_open = data_folder / "projects" / dataMap['osdp']['project'] / "vagrant"
            final_directory = os.path.join(current_directory, file_to_open)
        elif dataMap['osdp']['platform'] == 'docker':
            file_to_open = data_folder / "projects" / dataMap['osdp']['project'] / "docker"
            final_directory = os.path.join(current_directory, file_to_open)
        if os.path.exists(final_directory):
            self.logger.info("A project with that name already exists!")
            self.backup()
            try:
                shutil.rmtree(final_directory, onerror=onerror)
                self.logger.info("The folder has been removed.!")
            except:
                self.logger.info("The folder could  not be removed.!")
        else:
            os.makedirs(final_directory)
        if dataMap['osdp']['linux'] not in self.linux:
            self.logger.info("The linux distro you selected is not supported yet!")
            self.logger.info("Go back into the settings.yml file and assign the linux key: ubuntu, centos, amazon, debian, dcos-vagrant !")
            sys.exit(1)
        url = "https://github.com/james-knott/" + dataMap['osdp']['linux'] + ".git"
        self.logger.info("Downloading project files!")
        Repo.clone_from(url, final_directory , branch="master")
        if dataMap['osdp']['platform'] == 'docker':
            IMG_SRC = dataMap['osdp']['dockerdeveloperimage']
            client = docker.Client()
            client.login(username=dataMap['osdp']['dockerhubusername'], password=dataMap['osdp']['dockerhubpassword'], registry="https://index.docker.io/v1/")
            client.pull(IMG_SRC)
            client.tag(image=dataMap['osdp']['dockerdeveloperimage'], repository=dataMap['osdp']['pushto'],tag=dataMap['osdp']['runtime'])

    def zipfolder(self):
        dt = datetime.datetime.now()
        datestring = dt.strftime('%m/%d/%Y')
        foldername = "osdpbackup"
        target_dir = os.getcwd()
        zipobj = zipfile.ZipFile(foldername + '.zip', 'w', zipfile.ZIP_DEFLATED)
        rootlen = len(target_dir) + 1
        for base, dirs, files in os.walk(target_dir):
            for file in files:
                fn = os.path.join(base, file)
                zipobj.write(fn, fn[rootlen:])


    def start(self, projectname):
        dataMap = self.get_settings()
        current_directory = os.getcwd()
        data_folder = Path("osdp")
        file_to_open = data_folder / "projects" / dataMap['osdp']['project'] / dataMap['osdp']['platform']
        final_directory = os.path.join(current_directory, file_to_open)
        if not os.path.exists(final_directory):
            print("This should have already been created")
            exit()
        if dataMap['osdp']['platform'] == 'vagrant':
            vagrant_folder = Path(final_directory)
            v = vagrant.Vagrant(vagrant_folder, quiet_stdout=False)
            try:
                v.up()
            except Exception as e:
                pass
            os.chdir(vagrant_folder)
            cmdCommand = "vagrant port"
            process = subprocess.Popen(cmdCommand.split(), stdout=subprocess.PIPE)
            output, error = process.communicate()
            print(output)
        elif dataMap['osdp']['platform'] == 'docker':
            print("Ths platform is docker and we will connect to the image")
            os.chdir(final_directory)
            retval = os.getcwd()
            IMG_SRC = dataMap['osdp']['dockerdeveloperimage']
            client = docker.Client()
            client.login(username=dataMap['osdp']['dockerhubusername'], password=dataMap['osdp']['dockerhubpassword'], registry="https://index.docker.io/v1/")
            client.pull(IMG_SRC)
            client.tag(image=dataMap['osdp']['dockerdeveloperimage'], repository=dataMap['osdp']['pushto'],tag=dataMap['osdp']['runtime'])
            response = [line for line in client.push(dataMap['osdp']['pushto'] + ":" + dataMap['osdp']['runtime'], stream=True)]
            container_id = client.create_container('buildmystartup/ghettolabs:python3.6',stdin_open=True,tty=True,command='/bin/bash', volumes=['/home/user/environments/osdp/osdp/projects/ghettolabs/docker'],host_config=client.create_host_config \
            (binds=['/home/user/environments/osdp/osdp/projects/ghettolabs/docker:/var/task',]))
            dockerpty.start(client, container_id)

    def stop(self, projectname):
        dataMap = self.get_settings()
        current_directory = os.getcwd()
        data_folder = Path("osdp")
        file_to_open = data_folder / "projects" / projectname / "vagrant"
        final_directory = os.path.join(current_directory, file_to_open)
        if not os.path.exists(final_directory):
            os.makedirs(final_directory)
        vagrant_folder = Path(final_directory)
        v = vagrant.Vagrant(vagrant_folder, quiet_stdout=False)
        v.halt()

    def update(self):
        self.new()

    def backup(self):
        yaml = YAML()
        self.logger.info("Backing up projects to S3.!")
        foldername = "osdpbackup"
        dt = datetime.datetime.now()
        datestring = dt.strftime('%m_%d_%Y')
        foldername = "osdpbackup"
        with open(r"osdp/configuration/settings.yml") as f:
            dataMap = yaml.load(f)
            local_directory = os.getcwd()
            mybucket = "osdp-backups-" + dataMap['osdp']['username']
            destination = 'OSDP'
            region = 'us-west-2'
            conn = boto3.resource('s3',region_name="us-west-2")

            if not conn.Bucket(mybucket) in conn.buckets.all():
                print('creating bucket ' + mybucket + '...')
                try:
                    conn.create_bucket(Bucket=mybucket, CreateBucketConfiguration={'LocationConstraint': 'us-west-2'})
                except botocore.exceptions.ClientError as e:
                    print('Error: ' + e.response['Error']['Message'])
            else:
                print('bucket ' + mybucket + ' already exists')

            self.zipfolder()
            client = boto3.client('s3')
            session = boto3.Session(region_name='us-west-2')
            s3 = session.resource('s3')
            s3bucket = s3.Bucket(mybucket)
            s3.Bucket(mybucket).upload_file('osdpbackup.zip', "osdp" + "/" + datestring + "/" + "osdpbackup.zip")

    def destroy(self, projectname):
        dataMap = self.get_settings()
        current_directory = os.getcwd()
        data_folder = Path("osdp")
        file_to_open = data_folder / "projects" / projectname / "vagrant"
        final_directory = os.path.join(current_directory, file_to_open)
        if not os.path.exists(final_directory):
            os.makedirs(final_directory)
        vagrant_folder = Path(final_directory)
        v = vagrant.Vagrant(vagrant_folder, quiet_stdout=False)
        v.destroy()

    def get_settings(self):
        yaml = YAML()
        if os.path.isfile('osdp/configuration/settings.yml'):
            with open(r"osdp/configuration/settings.yml") as f:
                dataMap = yaml.load(f)
                return dataMap
        else:
            self.logger.info("Could not find settings file. Downloading new copy. Please edit then run osdp --new again!")
            self.init()







