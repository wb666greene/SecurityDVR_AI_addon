# SecurityDVR_AI_addon
A simple, relatively inexpensive, demo/development system to add AI to a security system DVR using a Raspberry Pi 3 and an Intel Movidius Neural Compute Stick.   This is not a project/product I plan to peddle, I'm not the first to think of doing this, but I'm finally far enough along with help from some fantastic open source projects (to be credited below) that I think I can help jumpstart others with similar ideas.

## Hardware Requirements
### AI Host 
Raspberry Pi3             ~$35 (us),
Movidius NCS              ~$80,
SD card 32GB recommended  ~$15,
5V 2.4A power supply      ~$10,
USB extension cable       ~$8   (as NCS blocks all other USB ports on the Pi).  If you really plan to use the system you will want an external USB harddrive or memory stick to store the images.  While developing this I had been using an external USB hard drive to store the images for the ~3 years I'd been trying to get to where I've finally arrived, it died soon after I got the system live so I replaced it with a USB memory stick and I'll see how it holds up.  This system is the stripped down essence of what I am currently running with my FLIR Lorex security DVR, which is full of ugly code to work around the lameness of my Lorex DVR.

### World's least expensive security DVR (or use what you have if it can ftp snapshots)
Raspberry PiZero-W        ~$10  (any Pi model that can run MotioneyeOS will work),
PiCamera (NoIR recommended) ~$30,
5V 1.2A power supply      ~$5   (I used one from an old cell phone),
SD card 16 GB minimum     ~$8.

### Essential for installation & setup, very useful in general (mundane Pi stuff)
HDMI monitor 1920x1080 (cheap now, so why hassle with anything less),
HDMI video cable,
USB keyboard & mouse,
Internet connection (with WiFi access for the PiZero-W, does anyone not have wifi these days?),
USB OTG cable for PiZero-W (and USB hub for PiZero-W if keyboard and mouse don't share a port),
Mini-HDMI to HDMI adaptor for the PiZero-W (unless you are expert enough to set it up "headless"),
Suitable cases for the Pi3 and PiZero-W (I used the "official" Pi Foundation cases to support them a bit, others are less expensive and arguably better, especially if you want the camera module inside the case with other than a PiZero).

## Base software
### AI host
Install latest Raspbian "stretch" and Movidius sdk (API only) as clearly described here:
https://www.pyimagesearch.com/2018/02/12/getting-started-with-the-intel-movidius-neural-compute-stick/
#### Extra required software:
mqtt, node-red-contrib-ftp-server, paho-mqtt, sample code from here:
https://www.pyimagesearch.com/2018/02/19/real-time-object-detection-on-the-raspberry-pi-with-the-movidius-ncs/
to get the precompiled mobilenetgraph file for the NCS, and the python script I started with, along with a nice code walk through that will help you understand what is going on and see how simple my changes really were. I believe the mobilenetgraph file came from here:
https://github.com/chuanqi305/MobileNet-SSD




