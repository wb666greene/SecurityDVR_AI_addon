# SecurityDVR_AI_addon
A simple, relatively inexpensive, demo/development system to add AI to a video security system DVR using a Raspberry Pi 3 and an Intel Movidius Neural Compute Stick.   This is not a project/product I plan to peddle, I'm not the first to think of doing this, but I'm finally far enough along with help from some fantastic open source projects (to be credited below) that I think I can help jumpstart others with similar ideas, whom I'd hope would share to evolve this into a easy to use system to make late night news broadcasts of security camera footage with pleas of "if you recognize them contact Crimestoppers" a thing of the past becasue timely push notification to a responsible party gets the police on the scene fast enough to catch the vermin red-handed!

##Photos of the demo system:
https://github.com/wb666greene/SecurityDVR_AI_addon/wiki/AI-Host-Installation

## Hardware Requirements
### AI Host 
- Raspberry Pi3 (B+ preferred)  ~$35 (us),
- Movidius NCS                  ~$80,
- SD card 32GB recommended      ~$15,
- 5V 2.4A power supply          ~$10,
- USB extension cable           ~$8   (as NCS blocks all other USB ports on the Pi).  
- If you really plan to use the system you will want an external USB harddrive or memory stick to store the images.  While developing this I had been using an external USB hard drive to store the images for the ~3 years I'd been trying to get to where I've finally arrived, it died soon after I got the system live so I replaced it with a USB memory stick and I'll see how it holds up.  This project is the stripped down essence of what I am currently running with my FLIR Lorex security DVR, which is full of ugly code to work around the lameness of my Lorex DVR.

### World's least expensive security DVR (or use what you have if it can ftp snapshots, can't they all?)
- Raspberry PiZero-W          ~$10  (any Pi or alternative that can run MotioneyeOS will work),
- PiCamera (NoIR recommended) ~$30, (Makerfocus makes a nice one with built-in IR LEDs)
- 5V 1.2A power supply        ~$5   (I used one from an old cell phone),
- SD card 16 GB minimum       ~$8.

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
After getting the Movidius installed and running install these extras:

mqtt, node-red-contrib-ftp-server, paho-mqtt, using apt-get, npm, and pip.  I hope to put up more detailed directions on the Wiki as soon as I figure out how to use it.

#### You will need the Movidius graph file and sample python code from here:

https://www.pyimagesearch.com/2018/02/19/real-time-object-detection-on-the-raspberry-pi-with-the-movidius-ncs/

to get the precompiled mobilenetgraph file for the NCS, and the python script that I started with, along with a nice code walk through that will help you understand what is going on and see how simple my changes really were. 

I believe the mobilenetgraph file came from here:

https://github.com/chuanqi305/MobileNet-SSD


#### Installation is very simple, but fragile at this point.
1. Once you've verified your Movidius installation and downloaded the Mobilenet-SSD graph and installed the extra stuff I used, all you have to do is download the project AI_detection.py script to the same sub-directory as the graphs directory from the PyImageSearch example.  (Or you could edit the AI_detection.py script to load it from the location where you have saved the graph file.) Next download the project ftpToMovidius.formatted.json file, import it into node-red and deploy it.
2. Configure your DVR to ftp jpeg "snapshots" to the node-red ftp server "flow" using port 31415 user pi with the password you've changed to after the Raspbian installation.
3. This is where one size doesn't fit all as different DVRs will want to impose a different directory layout on the server.  If you configure MotioneyeOS as in the next section as shown below it'll match the defaults.  Otherwise you need to edit the python script variables 
from the defautls (shown below) to match the paths your DVR wants to produce.
    - ftpdFQN="/home/pi/Meye/2018-05-20/10-35-12.jpg"
    - ftpdPath="/home/pi/Meye/2018-05-20"
    - ftpdTopic="/home/pi/Meye"
    - subscribeTopic="/home/pi/Meye/#"
4. With he AI Host booted to the GUI start the AI from a terminal with:
   - cd /path_to_where_you_put_it
   - python AI_detection.py -d 2
5. You can now test things by using an ftp client to upload some sample security camera snapshot images.  You should see the original image resized 300x300 to send to the Movidius in a small window, and if a person is detected in the image, the output with a box drawn around the person in a window that automatically resizes to original jpeg size.  Once you've gotten this far you are ready to let the DVR send files to the AI and see the results.
6.  Remember this is not a "ready to go" project, although I'd like to get it there with your help!
7.  I've been running my Lorex version for about two weeks now, with one Movidius and a Pi3 B+ handling snapshots from 9 cameras.


### MotioneyeOS DVR (if not using your existing one)

Get MotioneyeOS version approprate for your Pi or alternative, from here (Thank you @ccrisan/motioneyeos):

https://github.com/ccrisan/motioneyeos/wiki/Supported-Devices

Install and setup following his instruction Wiki which are much better than I could ever do:

https://github.com/ccrisan/motioneyeos/wiki/Installation

Configure to meet your needs as shown here:

https://github.com/ccrisan/motioneyeos/wiki/Configuration

- I recommend turning off "Movies" and "Notification"
- Motion detection needs to be on, set to snapshots on motion detection.
- Upload Media Files needs to be on


## ftp settings for MotioneyeOS or your existing DVR
  - Server:  IP or name (if DNS works on your LAN) of your AI Host, must be same subnet as DVR
  - Port: 31415 (clever ey?)
 

# Others thinking along the same line that I'm aware of:

https://github.com/debsahu/PiCamMovidius

This is pretty much the same function as the PyImageSearch real-time tutorial but using a PiZero-W instead of a Pi3, with MQTT added to use Home Automation for notifications.  Also seems he's found a pre-compiled OpenCV-3.2 and used it with YoLo network.  I was extremly impressed with Darknet YOLO, but it took 18 seconds to process an image on my i7 desktop, I never could get tinyYOLO to do anything.


