#!/bin/bash -e
# -e     >> return exit-code 1 if any error occurred

sudo yum -y update
sudo amazon-linux-extras install epel
sudo yum repolist
sudo yum -y install ansible
