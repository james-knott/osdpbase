## Features
- Manages mutiple vagrant environments
- YAML config file. 
- Library of working Vagrantfiles
- Automatic project backup to S3

## Requirements
- virtualbox 5.x
- vagrant >1.8.4
- Python 3.x
- Install requirements_osdp.txt
- amazon aws account (For S3 backups) 


## How to use
- download latest version (Clone or Download Zip) 
- Install requirements_osdp.txt
- Run osdpv3.py --init (Downloads template.yml file to get started)
- Edit the file osdp/template.yml and add your company name, project name, version of linux.
- Run osdpv3.py --new (This downloads the vagrantfile for you from this repo)
- Start osdp3.py --start company (company works well for me but can be any name or project) At the end it spits out port number.
- Connect with your favorite ssh client or navigate to project/company/vagrant and do a vagrant ssh
- When your done with the project or no longer want the vagrant environment just do osdpv3.py --destroy

## Developers
- Please use developer branch
- Create a virtualenv for your development and testing then move your code over to a clean folder to push up your changes.

## TODO:
- Make yaml = YAML() global so it is not scattered all over the place.
- Move start stop and destroy to one method.
- Add custom exceptions and assert. Basic testing.
- Add Dropbox sync
- clean up all os file system checks
- General refactor of all code to make pretty and perform better.
- Add state machine so that the application always knows what has been started.
- Make plugin system so users can add Vagrantfiles or profiles.
- Make it so the application can automatically pull from ansible-galaxy
