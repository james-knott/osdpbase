"""Open Source Development Platform Base Class.

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

__author__ = "James Knott (@Ghettolabs)"
__copyright__ = "Copyright 2018 James Knott"
__credits__ = ["James Knott"]
__license__ = "Apache License, 2.0"
__version__ = "0.0.3"
__maintainer__ = "James Knott"
__email__ = "devops@ghettolabs.io"
__status__ = "Development"

LOG_FILENAME = '/tmp/logging_osdp.out'

def setup_logging():
    logger = logging.getLogger()
    for h in logger.handlers:
      logger.removeHandler(h)
    h = logging.StreamHandler(sys.stdout)
    FORMAT = "[%(levelname)s %(asctime)s %(filename)s:%(lineno)s - %(funcName)21s() ] %(message)s"
    h.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(h)
    logger.setLevel(logging.DEBUG)
    return logger

yaml = YAML # Need to fix this so its global and not scattered all over.

class MyProgressPrinter(RemoteProgress):
            def update(self, op_code, cur_count, max_count=None, message=''):
                print(op_code, cur_count, max_count, cur_count / (max_count or 100.0), message or "Downloading....")



class OSDPBase():
    def __init__(self):
        self.current_directory = os.getcwd()
        self.final_directory = os.path.join(self.current_directory, r"osdp")
        self.directory = 'osdp'
        self.my_file = Path(r"osdp/keys/private.bin")
        self.secret_code = ''
        self.encoded_key = ''
        self.linux = ['ubuntu', 'centos', 'debian', 'amazon', 'dcos-vagrant', 'xenial', 'docker', 'amazonlinux', 'docker-lambda']
        self.logger = setup_logging()
    def init(self):
        try:
            Repo.clone_from('https://github.com/james-knott/osdp.git', self.final_directory , branch="master", progress=MyProgressPrinter())
            self.logger.info("Downloaded the settings.yml file. Go to osdp/template.yml to customize your environment!")
        except git.exc.GitCommandError as e:
            self.logger.info("Could not connect to github.com .!")
            if os.path.isfile('osdp/template.yml'):
                self.logger.info("Found the settings.yml file. It has already been downloaded!")
            else:
                self.logger.info("Could not connect to Github to download the settings.yml file. Creating Dynamically!")
                inp = """\
                # Open Source Development Platform
                 osdp:
                   # The choices are Ubuntu, Centos, or Amazon.
                   linux: ubuntu
                   # Username and password are used for remote accounts when needed. This will be encrypted.
                   username: jknott
                   password: password123
                   project: mynewproject
                   # Supported languages are Python, Node, Java, Go
                   language: Python
                   # Docker or Vagrant
                   platform: vagrant
                   # What cloud provider are you using? AWS, Google, DigitalOcean, Azure.
                   cloud: aws
                   # Where would you like your projects backed up to? S3 or Dropbox?
                   backups: s3
                   # What VCS will you be using? Github, Gitlab, Bitbucket.
                   scm: github
                """
                yaml = YAML()
                code = yaml.load(inp)
                #yaml.dump(code, sys.stdout) test what they dynamic file looks like
                self.logger("Your new projecct name is", code['osdp']['project'])
                if not os.path.exists(self.final_directory):
                    os.makedirs(self.final_directory)
                with open('osdp/template.yml', "w") as f:
                    yaml.dump(code, f)


    def new(self):
        yaml = YAML()
        if os.path.isfile('osdp/template.yml'):
            with open(r"osdp/template.yml") as f:
                dataMap = yaml.load(f)
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
                        self.logger.info("The folder has been remvoed.!")
                    except:
                        self.logger.info("The folder could  not be remvoed.!")
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
                    self.setup_docker(path=final_directory, dataMap=dataMap)
                # TODO: sed -i "s/^\(boxName\s*=\s*\).*\$/\1ahead/" Vagrantfile
        else:
            self.logger.info("Could not find settings file. Downloading new copy. Please edit then run osdp --new again!")
            self.init()


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
        with open(r"osdp/template.yml") as f:
            yaml = YAML()
            dataMap = yaml.load(f)
            current_directory = os.getcwd()
            data_folder = Path("osdp")
            file_to_open = data_folder / "projects" / dataMap['osdp']['project'] / dataMap['osdp']['platform']
            final_directory = os.path.join(current_directory, file_to_open)
            if not os.path.exists(final_directory):
                print("This should have already been created")
                exit()
                #os.makedirs(final_directory)
            if dataMap['osdp']['platform'] == 'vagrant':
                vagrant_folder = Path(final_directory)
                v = vagrant.Vagrant(vagrant_folder, quiet_stdout=False)
                try:
                    v.up()
                except Exception as e:
                    pass
                    #self.logger.error(traceback.format_exc())
                os.chdir(vagrant_folder)
                cmdCommand = "vagrant port"   #specify your cmd command
                process = subprocess.Popen(cmdCommand.split(), stdout=subprocess.PIPE)
                output, error = process.communicate()
                print(output)
            elif dataMap['osdp']['platform'] == 'docker':
                print("Ths platform is docker and we will connect to the image")
                os.chdir(final_directory)
                retval = os.getcwd()
                IMG_SRC = "buildmystartup/ghettolabs:python3.6"
                client = docker.Client()
                client.pull("buildmystartup/ghettolabs:python3.6")
                container_id = client.create_container('buildmystartup/ghettolabs:python3.6',stdin_open=True,tty=True,command='/bin/bash', volumes=['/home/user/environments/osdp/osdp/projects/ghettolabs/docker'],host_config=client.create_host_config \
                (binds=['/home/user/environments/osdp/osdp/projects/ghettolabs/docker:/var/task',]))
                dockerpty.start(client, container_id)

    def stop(self, projectname):
        with open(r"osdp/template.yml") as f:
            dataMap = yaml.load(f)
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
        with open(r"osdp/template.yml") as f:
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
        yaml = YAML()
        with open(r"osdp/template.yml") as f:
            dataMap = yaml.load(f)
            current_directory = os.getcwd()
            data_folder = Path("osdp")
            file_to_open = data_folder / "projects" / projectname / "vagrant"
            final_directory = os.path.join(current_directory, file_to_open)
            if not os.path.exists(final_directory):
                os.makedirs(final_directory)
            vagrant_folder = Path(final_directory)
            v = vagrant.Vagrant(vagrant_folder, quiet_stdout=False)
            v.destroy()

    def setup_docker(self, path, dataMap):
        print(path)
        username = dataMap['osdp']['dockerhubusername']
        password = dataMap['osdp']['dockerhubpassword']
        imagetag = dataMap['osdp']['runtime']
        os.chdir(path)
        # Test on Python 3.6 with a custom file named my_module.py containing a my_handler function
        #docker run --rm -v "$PWD":/var/task lambci/lambda:python3.6 my_module.my_handler
        #client = docker.from_env()
        #container = client.containers.run(lambci/lambda:myimage,'my_module.my_handler',detach=True)
        client = docker.from_env()
        client.login(username=dataMap['osdp']['dockerhubusername'], password=dataMap['osdp']['dockerhubpassword'])
        client.images.build(path=path, tag="buildmystartup/ghettolabs:" + imagetag)
        for line in client.images.push(repository="buildmystartup/ghettolabs", stream=True):
            print(line)






