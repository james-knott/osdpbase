"""Open Source Development Platform Base Class.

This module contains the base class for OSDP
(OSDPBase).

Things to do:
        TODO: Move start stop and destroy to one method.
        Removed: Move encryp and decrypt to separate methods.
        Done: Add custom exceptions for all file open operations.
        Done: s3 - Add Dropbox sync
        TODO: clean up all os file system checks
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
from Crypto.PublicKey import RSA
from Crypto import Random
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP
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





__author__ = "James Knott (@Ghettolabs)"
__copyright__ = "Copyright 2018 James Knott"
__credits__ = ["James Knott"]
__license__ = "Apache License, 2.0"
__version__ = "0.0.1"
__maintainer__ = "James Knott"
__email__ = "devops@ghettolabs.io"
__status__ = "Development"


def setup_logging():
    logger = logging.getLogger()
    for h in logger.handlers:
      logger.removeHandler(h)

    h = logging.StreamHandler(sys.stdout)

    # use whatever format you want here
    FORMAT = "[%(levelname)s %(asctime)s %(filename)s:%(lineno)s - %(funcName)21s() ] %(message)s"
    h.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

    return logger

yaml = YAML

class MyProgressPrinter(RemoteProgress):
            def update(self, op_code, cur_count, max_count=None, message=''):
                print(op_code, cur_count, max_count, cur_count / (max_count or 100.0), message or "Downloading....")



class OSDPBase(object):
    def __init__(self):
        self.current_directory = os.getcwd()
        self.final_directory = os.path.join(self.current_directory, r"osdp")
        self.directory = 'osdp'
        self.my_file = Path(r"osdp/keys/private.bin")
        self.secret_code = ''
        self.encoded_key = ''
        self.linux = ['ubuntu', 'centos', 'debian', 'amazon', 'dcos-vagrant', 'xenial']
        self.logger = setup_logging()
    def init(self):
        try:
            Repo.clone_from('https://github.com/james-knott/osdp.git', self.final_directory , branch="master", progress=MyProgressPrinter())
            self.logger.info("Downloaded the settings.yml file. Go to osdp/template.yml to customize your environment!")
        except git.exc.GitCommandError as e:
            #z = e
            #print(z)
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
                file_to_open = data_folder / "projects" / dataMap['osdp']['project'] / "vagrant"
                final_directory = os.path.join(current_directory, file_to_open)
                if os.path.exists(final_directory):
                    self.logger.info("A project with that name already exists!")
                    #self.backup()
                    try:
                        shutil.rmtree(final_directory, onerror=onerror)
                        self.logger.info("The folder has been remvoed.!")
                    except:
                        self.logger.info("The folder could  not be remvoed.!")
                    #os.makedirs(final_directory)
                else:
                    os.makedirs(final_directory)
                if dataMap['osdp']['linux'] not in self.linux:
                    self.logger.info("The linux distro you selected is not supported yet!")
                    self.logger.info("Go back into the settings.yml file and assign the linux key: ubuntu, centos, amazon, debian, dcos-vagrant !")
                    sys.exit(1)
                url = "https://github.com/james-knott/" + dataMap['osdp']['linux'] + ".git"
                self.logger.info("Downloading project files!")
                Repo.clone_from(url, final_directory , branch="master")
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
        #with open(r"osdp\template.yml") as f:
            #      dataMap = yaml.load(f)
            current_directory = os.getcwd()
            data_folder = Path("osdp")
            file_to_open = data_folder / "projects" / projectname / "vagrant"
            final_directory = os.path.join(current_directory, file_to_open)
            if not os.path.exists(final_directory):
                os.makedirs(final_directory)
            print(final_directory)
            vagrant_folder = Path(final_directory)
            print(vagrant_folder)
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



