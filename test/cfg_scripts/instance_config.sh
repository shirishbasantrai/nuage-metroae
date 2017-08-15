#!/bin/bash
# VM Automation of Instance Configuration Script

centosver="$1"
minorver=${centosver:0:3}
frontendIP=$(ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1)
gwIP=${frontendIP:0:9}
gwIP="${gwIP}1"

echo "--> Adding IP and hostname to /etc/hosts"

hostname=$(hostname)

echo $frontendIP "   " $hostname >> /etc/hosts

echo "--> Updating /etc/resolv.conf file"
echo "--> by adding DNS servers to file"

dns1="128.251.10.25"
dns2="128.251.10.29"

FILE="/etc/resolv.conf"

echo -e "# Generated by VM Automation of Instance Configuration Script \nnameserver $dns1 \nnameserver $dns2" >$FILE

echo "--> Changing StrictHostKeyChecking to no"

find='StrictHostKeyChecking ask'
replace='StrictHostKeyChecking no'

sed -i 's/$find/$replace/' /etc/ssh/ssh_config

echo "--> Running yum update for desired version of CentOS"

find='vault.centos.org'
replace='mirror.centos.org'

if [ $minorver = "7.3" ]
then
   sed -i '/baseurl=/s/^/#/g' /etc/yum.repos.d/CentOS-Base.repo
   sed -i "s#"$find"#"$replace"#g" /etc/yum.repos.d/CentOS-Base.repo
   sed -i "s#"$find"#"$replace"#g" /etc/yum.repos.d/CentOS-CR.repo
   yum -y update
fi

if [ $minorver != "7.3" ]
then
   yum -y --releasever=$centosver update
fi

echo "--> Installing basic packages for VM procedures"

yum -y install ntp dnsmasq qemu-kvm libvirt libguestfs-tools libvirt-python java

echo "--> Destroying default virtual network"

service libvirtd restart

virsh net-destroy default
virsh net-undefine default

echo "--> Configuring initial bridge based on given IP"
echo "--> Will eventually change to search for IP"

FILE="/etc/sysconfig/network-scripts/ifcfg-eth0"

/bin/cat <<EOM >$FILE
# Generated by VM Automation of Instance Configuration Script
DEVICE="eth0"
NAME="eth0"
TYPE=Ethernet
BRIDGE="br-eth0"
PEERROUTES=no
PEERDNS=no
IPV6INIT=no
MTU=9000
EOM

FILE="/etc/sysconfig/network-scripts/ifcfg-br-eth0"

/bin/cat <<EOM >$FILE
DEVICE="br-eth0"
NAME="br-eth0"
TYPE=Bridge
BOOTPROTO=static
ONBOOT=yes
DELAY=0
DEFROUTE=yes
PEERROUTES=no
IPV6INIT=no
MTU=9000
IPADDR=$frontendIP
PREFIX=24
GATEWAY=$gwIP
DNS1=$dns1
DNS2=$dns2
EOM

echo "--> Restarting network with new bridge"

systemctl restart network

echo "--> Beginning configurations for Jenkins"

echo "--> Downloading all dependencies"
echo "--> Including: git, python, python2-pip"
echo "    gcc epel-release, openSSL, pyOpenSSL"
echo "    ansible v2.2.1, netmiko, netaddr,  "
echo "    ipaddress, pexpect, vspk, and flake8"

yum -y install git epel-release python-devel openssl-devel libguestfs-tools gcc
yum -y install python2-pip
pip install pyOpenSSL
pip install ansible==2.2.1
pip install netmiko netaddr ipaddress pexpect vspk flake8

echo "--> Creating swapfile to ensure sufficient"
echo "    memory space for Jenkins"

dd if=/dev/zero of=/swapfile count=16000 bs=1M
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile