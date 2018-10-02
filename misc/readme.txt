Installation instructios for Raspberry pi running a fresh install of Raspbian Stretch Lite:

sudo apt-get install python-pip python-pygame python-serial xserver-xorg xinit

Copy the following files to pi home directory:
.xinitrc
pysca.service
runviscapi

Edit file:
/etc/X11/X
to contain:
allowed_users=anybody

Additionally:
sudo systemctl enable /pol/ku/pysca.service

