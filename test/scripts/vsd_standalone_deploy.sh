#!/bin/sh
set -e
cp ./test/files/setup.yml.VSDStandalone ./setup.yml
ansible-playbook setup.yml -vvvv
ansible-playbook reset_build.yml -vvvv
ansible-playbook build.yml -vvvv
./metro-ansible test.yml -vvvv
