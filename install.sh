spinner()
{
local pid=$1
local delay=0.1
local spinstr='|/-\'
echo "$pid" > "/tmp/.spinner.pid"
echo ""
printf " $2 "
while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
local temp=${spinstr#?}
printf " [%c]  " "$spinstr"
local spinstr=$temp${spinstr%"$temp"}
sleep $delay
printf "\b\b\b\b\b\b"
done
printf "    \b\b\b\b"
}

tput reset
tput civis



echo "########## Carius Installation ##########"
echo "Ensure that you have an active Internet connection with an acceptable speed (at least 10Mbps recommended)"
# First step is to check whether you are logged in as root
# and which Ubuntu version is running. Carius requires 18.04 or later

if [[ `id -u` != 0 ]]; then
echo "Must be root to run script"
exit
fi

wget -q --spider http://google.com

if [ $? -eq 0 ]; then
echo "There is an active Internet connection"
else
echo "Offline. Check your Internet connection"
exit
fi

UbuntuRelease=$(lsb_release -rs)

if [ "`echo "${UbuntuRelease} < 18.04" | bc`" -eq 1 ]; then
echo "System requirement is Ubuntu LTS 18.04 or higher"
exit
else
IFS=':' read -r var1 var2 <<< "$(lsb_release -d)"
echo "Installing Carius on $var2"
fi

# Second step is to upgrade and update Ubuntu

add-apt-repository universe -y  > /dev/null
(dpkg --configure -a > /dev/null) & spinner $! "Verify DPKG consistency....."
(DEBIAN_FRONTEND=noninteractive apt-get -qq upgrade  &>/dev/null) & spinner $! "Upgrading the system to ensure that it is up to date....."
(DEBIAN_FRONTEND=noninteractive apt-get -qq update  &>/dev/null) & spinner $! "Updating the system to ensure that it is up to date....."




# Next is to install all the dependencies

(DEBIAN_FRONTEND=noninteractive apt-get -qq -y -o=Dpkg::Use-Pty=0 install net-tools  &>/dev/null) & spinner $! "Installing Net tools....."
(DEBIAN_FRONTEND=noninteractive apt-get -qq -y -o=Dpkg::Use-Pty=0 install dos2unix  &>/dev/null) & spinner $! "Installing Dos2Unix....."
(DEBIAN_FRONTEND=noninteractive apt-get -qq -y -o=Dpkg::Use-Pty=0 install tshark  &>/dev/null) & spinner $! "Installing Tshark....."
(DEBIAN_FRONTEND=noninteractive apt-get -qq -y -o=Dpkg::Use-Pty=0 install apache2 &> /dev/null) & spinner $! "Installing Apache2....."
(DEBIAN_FRONTEND=noninteractive apt-get -qq -y -o=Dpkg::Use-Pty=0 install tftpd &> /dev/null) & spinner $! "Installing TFTP Daemon....."
(DEBIAN_FRONTEND=noninteractive apt-get -qq -y -o=Dpkg::Use-Pty=0 install tftp  &> /dev/null) & spinner $! "Installing TFTP Client....."
(DEBIAN_FRONTEND=noninteractive apt-get -qq -y -o=Dpkg::Use-Pty=0 install mysql-server &> /dev/null) & spinner $! "Installing Mysql Server....."
(DEBIAN_FRONTEND=noninteractive apt-get -qq -y -o=Dpkg::Use-Pty=0 install mysql-client &> /dev/null) & spinner $! "Installing Mysql Client....."

if ! [ -x "$(command -v python3)" ]; then
echo 'Error: Python is not installed or it is the incorrect command. Carius requires the   python3   command' >&2
exit 1
fi

# Create tftp folder

if [ ! -d "/home/tftpboot" ]; then
mkdir /home/tftpboot
fi

chmod -R 777 /home/tftpboot
chown -R nobody /home/tftpboot

# Create the configuration file for TFTP

cat > /etc/xinetd.d/tftp  << ENDOFFILE
service tftp
{
protocol        = udp
port            = 69
socket_type     = dgram
wait            = yes
user            = nobody
server          = /usr/sbin/in.tftpd
server_args     = /home/tftpboot
disable         = no
}
ENDOFFILE

# Restart TFTP daemon

service xinetd restart

# Install the Python modules

(DEBIAN_FRONTEND=noninteractive apt-get -y install -qq -o=Dpkg::Use-Pty=0 python3-pip &> /dev/null) & spinner $! "Installing Python3 PIP....."

(pip3 install --default-timeout=100 requests > /dev/null) & spinner $! "Installing Python3 requests library....."
(pip3 install --default-timeout=100 pygal > /dev/null) & spinner $! "Installing Python3 pygal library....."
(pip3 install --default-timeout=100 flask> /dev/null) & spinner $! "Installing Python3 flask library....."
(pip3 install --default-timeout=100 flask-bootstrap > /dev/null) & spinner $! "Installing Python3 flask bootstrap library....."
(pip3 install --default-timeout=100 flask-login > /dev/null) & spinner $! "Installing Python3 flask login library....."
(pip3 install --default-timeout=100 pycryptodome > /dev/null) & spinner $! "Installing Python3 pycryptodome library....."
(pip3 install --default-timeout=100 pymysql > /dev/null) & spinner $! "Installing Python3 pymysql library....."
(pip3 install --default-timeout=100 schedule > /dev/null) & spinner $! "Installing Python3 schedule library....."
(pip3 install --default-timeout=100 scapy > /dev/null) & spinner $! "Installing Python3 scapy library....."
(pip3 install --default-timeout=100 psutil > /dev/null) & spinner $! "Installing Python3 psutil library....."
(pip3 install --default-timeout=100 paramiko > /dev/null) & spinner $! "Installing Python3 paramiko library....."
(pip3 install --default-timeout=100 waitress > /dev/null) & spinner $! "Installing Python3 waitress library....."

# Mysql user, database and table structure creation
# Depending on the Mysql version, the structure is different

varA=($(echo $(mysql -uroot -e "select version();") | tr ')' '\n'))
varB=($(echo "${varA[1]}" | tr '-' '\n'))
varC=($(echo "${varB[0]}" | tr '.' '\n'))
mysqlversion=${varC[0]}${varC[1]}

if [[ "$mysqlversion" < "80" ]] ;
then
 mysql -uroot < ./doc/mysqltable57.txt
else
 mysql -uroot < ./doc/mysqltable80.txt
fi

echo ""
echo " Installing the app"
cp ./__init__.py /var/www/html/__init__.py  > /dev/null
cp ./startapp.sh /var/www/html/startapp.sh  > /dev/null
cp ./views/ /var/www/html/ -r > /dev/null
cp ./static/ /var/www/html/ -r > /dev/null
cp ./templates/ /var/www/html/ -r > /dev/null
cp ./classes/ /var/www/html/ -r > /dev/null
cp ./bash/ /var/www/html/ -r > /dev/null

if [ ! -d "/var/www/html/images" ]; then
mkdir /var/www/html/images
fi
chmod 777 /var/www/html/images/
chmod 777 /var/www/html/images

echo " Configuring the app"

activeInterface=$(route | grep '^default' | grep -o '[^ ]*$')
cat > /var/www/html/bash/globals.json  << ENDOFFILE
{"idle_timeout": "3000", "pcap_location": "/var/www/html/bash/trace.pcap", "retain_dhcp": "30", "retain_snmp": "30", "retain_syslog": "30", "secret_key": "ArubaRocks!!!!!!", "appPath": "/var/www/html/", "softwareRelease": "1.1", "sysInfo": "","activeInterface":"$activeInterface"}
ENDOFFILE
chmod 777 /var/www/html/bash/listener.sh
chmod 777 /var/www/html/bash/cleanup.sh
chmod 777 /var/www/html/bash/topology.sh
chmod 777 /var/www/html/bash/trackers.sh
chmod 777 /var/www/html/bash/ztp.sh

dos2unix -q /var/www/html/startapp.sh >/dev/null
chmod 777 /var/www/html/startapp.sh
chmod +x /var/www/html/startapp.sh

tput cnorm

# Final step is to automatically start the startapp.sh when the system boots

cat > /etc/systemd/system/carius.service  << ENDOFFILE
[Unit]
Description=Carius
After=mysql.service
[Service]
Type=simple
WorkingDirectory=/var/www/html
ExecStart=/var/www/html/startapp.sh
[Install]
WantedBy=default.target
ENDOFFILE

chmod 664 /etc/systemd/system/carius.service
systemctl daemon-reload &> /dev/null
systemctl enable carius.service &> /dev/null
systemctl start carius.service &> /dev/null

echo " ######### Carius installation completed ##########"
echo " Navigate with your browser to http://a.b.c.d:8080   where a.b.c.d is the IP address of the Carius server"
echo " The default login credentials are:"
echo " Username:  admin"
echo " There is no password, you are prompted to change the admin password after login as admin user"
echo ""
