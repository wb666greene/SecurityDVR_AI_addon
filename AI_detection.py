#!/usr/bin/env python

# AI_detection.py  derived from: ncs_realtime_objectdetection.py 7May18wbk
# Original code and tutorial:
#	https://www.pyimagesearch.com/2018/02/19/real-time-object-detection-on-the-raspberry-pi-with-the-movidius-ncs/
# Modified to run AI object detection on image sequences instead of PiCam video stream using Movidius Neuro Compute Stick
#
# USAGE
# changed defaults 9May16wbk
# Command: python AI_detection.py
# will default to using graphs/mobilenetgraph
#
# python AI_detection.py --graph graphs/mobilenetgraph
# will use an alternate NCS graph, but their be issues with using a different graph file!
#
# python AI_detection.py --graph graphs/mobilenetgraph --confidence 0.76 --display 0
# will let you change all the defaults (shown)
#
# Get path to image files via MQTT 8MAY18wbk
# currently input images are assumed to be size 704x480 from Lorex DVR "snapshots"  This restriction remove 19May19wbk
#
# 13May18wbk
# I developed this with the ftpd, Samba server, and node-red running on AlarmPi headless Pi2 running Raspbian "Jessie".
# The node-red flow is saved in the file: AlarmPi_flow.formatted.json and conncets to the MQTT server on Alarmbone Beaglebone
# computer that interfaces the PIR and handles alarm system states "Email" "Audio" "Idle".
# The node-red flow filters the filenames ftpd receives based on PIR motion detectors that cover the camera fied of view.
# The Lorex video motion detection is useless basically just "if n pixels changed in x amount of time its motion", pitiful.
# Unfortunately PIR motion detectors false trigger as the sun moves accross the sky or dark fast moving clouds pass by, so 
# PIR motion detectors don't solve the false motion problems unless the field of view doesn't include significant natural
# light or cycling heating/cooling sources.
#
# This program was developed on a Pi3 running Raspbian "Stretch" networked with AlarmPi and Alarmbone. I plan to move it to
# run on AlarmPi upgraded to a  Pi3 B+ (for faster ethernet connection to the Lorex) and use an MQTT server running on it
# to keep lorex the Lorex topic MQTT messages local.  17May18wbk the port went well but the Lorex snapshot rate is less
# than I'd like.
#
#19May18wbk
# Modified to use a simplified node-red flow to be the ftp server and write the files to a local directory sending
# the filenames to this AI_detection script via MQTT for a simple way to demo the ideas behind the system.
# Use a PiZeroW with PiCamera running MotioneyeOS to be the DVR.  Simple and relatively inexpensive 
# system to duplicate -- Movidius NCS ~$80, Pi3 ~$30-35, PiZeroW ~$10, PiCamera module ~$30, + power supplies and suitable cases.
# the mundane keyboard, monitor, cables, etc. are not really needed for development, as it all can be done via ssh, but IMHO 
# it really helps with the initial setup of Raspbian and MotioneyeOS to have a KVM.
# MotioneyeOS has a decent enough video motion detector that adding a PIR didn't seem to be worth the trouble.
#
# Other than removing all the crap to support the FLIR Lorex DVR lameness, the major change was to automatically handle various input image frame sizes.
# Sorry, but I hate Python's significant whitespace feature and use a 43" 4K monitor with 160 column editors/xterms for my work.
 

# import the necessary packages
from mvnc import mvncapi as mvnc
import argparse
import numpy as np
import time
import cv2
import paho.mqtt.client as mqtt
import time
import os


# MQTT server used by the node-red flow for sending the filenames to be analyzed
MQTTserver="localhost"
# these are basically where the ftp client wants to put the files on the server
# and are used in the on_message() mqtt callback
# These reflect the settings used in the MotioneyeOS setup
ftpdPath="/home/pi/Meye/2018-05-20"
ftpdFQN="/home/pi/Meye/2018-05-20/10-35-12.jpg"
ftpdTopic="/home/pi/Meye"
subscribeTopic="/home/pi/Meye/#"


# initialize the list of class labels our network was trained to
# detect, then generate a set of bounding box colors for each class
# Problem:  if a different neural net graph is passed in as a parameter these are
# unlikely to be correct for it, so the CLASSES labels need to be parameterized as well!
CLASSES = ("background", "aeroplane", "bicycle", "bird",
	"boat", "bottle", "bus", "car", "cat", "chair", "cow",
	"diningtable", "dog", "horse", "motorbike", "person",
	"pottedplant", "sheep", "sofa", "train", "tvmonitor")
COLORS = np.random.uniform(0, 255, size=(len(CLASSES), 3))
COLORS[15] = (250,250,250)	# force person box to be white, security cam inages tend to be dark especially in IR illumination

# Folllowing the example in:  https://www.pyimagesearch.com/2018/05/14/a-gentle-guide-to-deep-learning-object-detection
# objects to ignore if detected
IGNORE = set(["aeroplane", "boat", "bottle", "bus", "chair", "diningtable","pottedplant", "sofa", "train", "tvmonitor"])

# frame dimensions should match what what the neural net was trained with.
PREPROCESS_DIMS = (300, 300)
#input image size, set by Lorex DVR
DISPLAY_DIMS = (704, 480)		#default, is now reset dynamically on every input image received via MQTT


## functions
def preprocess_image(input_image):
	# preprocess the image
	preprocessed = cv2.resize(input_image, PREPROCESS_DIMS)
	preprocessed = preprocessed - 127.5
	preprocessed = preprocessed * 0.007843
	preprocessed = preprocessed.astype(np.float16)
	# return the image to the calling function
	return preprocessed


def predict(image, graph):
	# preprocess the image
	image = preprocess_image(image)
	# send the image to the NCS and run a forward pass to grab the
	# network predictions
	graph.LoadTensor(image, None)
	(output, _) = graph.GetResult()
	# grab the number of valid object predictions from the output,
	# then initialize the list of predictions
	num_valid_boxes = output[0]
	predictions = []
	# loop over results
	for box_index in range(num_valid_boxes):	# last index is tvmonitor which is not relavent
		# calculate the base index into our array so we can extract
		# bounding box information
		base_index = 7 + box_index * 7
		# boxes with non-finite (inf, nan, etc) numbers must be ignored
		if (not np.isfinite(output[base_index]) or
			not np.isfinite(output[base_index + 1]) or
			not np.isfinite(output[base_index + 2]) or
			not np.isfinite(output[base_index + 3]) or
			not np.isfinite(output[base_index + 4]) or
			not np.isfinite(output[base_index + 5]) or
			not np.isfinite(output[base_index + 6])):
			continue
		# extract the image width and height and clip the boxes to the
		# image size in case network returns boxes outside of the image boundaries
		(h, w) = image.shape[:2]
		x1 = max(0, int(output[base_index + 3] * w))
		y1 = max(0, int(output[base_index + 4] * h))
		x2 = min(w,	int(output[base_index + 5] * w))
		y2 = min(h,	int(output[base_index + 6] * h))
		# grab the prediction class label, confidence (i.e., probability),
		# and bounding box (x, y)-coordinates
		pred_class = int(output[base_index + 1])
		pred_conf = output[base_index + 2]
		pred_boxpts = ((x1, y1), (x2, y2))
		# create prediciton tuple and append the prediction to the predictions list
		prediction = (pred_class, pred_conf, pred_boxpts)
		# my initial kludge to ignore one class sometime in my camers field of view
		#if pred_class != 20:	# filter out prediction of tvmonitor which is not relavent for alarm system monitoring
		# Better way from apyImageSeach tutorial
		if not CLASSES[pred_class] in IGNORE:
			predictions.append(prediction)
	# return the list of predictions to the calling function
	return predictions


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(subscribeTopic)


# The callback for when a PUBLISH message is received from the server, aka message from SUBSCRIBE topic.
# typical filepath from Motioneye:  "/home/pi/Meye/2018-05-20/10-35-12.jpg"
# this bit of code will likely be DVR depenent and probably should be parameterized
inName=""		# file name via MQTT node-red on alarmPi
LorexMode=""	# will be Email, Audio, or Idle  via MQTT from alarmboneServer
def on_message(client, userdata, msg):
	global inName
	global LorexMode	# not used here, would be Email, Audio, or Idle 
	if msg.topic == "/home/pi/Meye/Mode":
		print(msg.topic+"  "+str(msg.payload))
		LorexMode = str(msg.payload)
	elif str(msg.topic).startswith(ftpdTopic) == True:
		# msg.topic is the ftpdFQN, perhaps I'm abusing MQTT but it simplifies thinks
		inName=str(msg.topic)
		#print inName
		folder=inName[:len(ftpdPath)]
		#print folder
		if os.path.exists(folder) == False:
			#print folder
			os.mkdir(folder)
			#print inName
		# write the file from motioneye
		if args["save"] > 0:
			outfile=open(inName,'wb')
		else:
			outfile=open("discardMe.jpg",'wb')
		outfile.write(msg.payload)
		outfile.close()
	else:	
		inName=""


def on_publish(client, userdata, mid):
    #print("mid: " + str(mid))		# don't think I need to care about this for now, print for initial tests
    pass


def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Unexpected disconnection!")
	pass


## Get things started!
# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-g", "--graph", default="./graphs/mobilenetgraph", help="optional path to input Movidius graph file")
ap.add_argument("-c", "--confidence", default=0.76, help="optional detection threshold, default 0.76")
# running headless (AlarmPi)want display default=0
ap.add_argument("-d", "--display", type=int, default=0, help="1 to display detected image on screen 2 displays NCS input and detected images")
# I default to saving the input images from the DVR for troubleshooting and perhaps future retraining
ap.add_argument("-s", "--save", type=int, default=1, help="1 to save original image in ftp Path, 0 to discard the original input images")
args = vars(ap.parse_args())

# grab a list of all NCS devices plugged in to USB
print("[INFO] finding NCS devices...")
devices = mvnc.EnumerateDevices()

# if no devices found, exit the script
if len(devices) == 0:
	print("[INFO] No devices found. Please plug in a NCS")
	quit()

# use the first device since this is a simple test script
# (you'll want to modify this is using multiple NCS devices)
print("[INFO] found {} devices. device0 will be used. "
	"opening device0...".format(len(devices)))
device = mvnc.Device(devices[0])
device.OpenDevice()

# open the CNN graph file
print("[INFO] loading the graph file into RPi memory...")
with open(args["graph"], mode="rb") as f:
	graph_in_memory = f.read()

# load the graph into the NCS
print("[INFO] allocating the graph on the NCS...")
graph = device.AllocateGraph(graph_in_memory)

# connect to MQTT broker
print("[INFO] connecting to MQTT broker...")
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_publish = on_publish
client.on_disconnect = on_disconnect
client.will_set("AI/Status", "AI sub-system has died!", 2, True)  # let everyone know we have died, perhaps node-red can restart it
client.connect(MQTTserver, 1883, 60)
client.publish("AI/Status", "AI running.", 2, True)

if args["display"] > 0:
	cv2.namedWindow("Detector Output")
	if args["display"] == 2:
		cv2.namedWindow("AI Input")
		cv2.moveWindow("AI Input",  10,  40)
		cv2.moveWindow("Detector Output",  25 + PREPROCESS_DIMS[0],  40)
	else:
		cv2.moveWindow("Detector Output",  10,  40)

while True:
	try:
		if len(inName) >= len(ftpdPath):
			#print "Processing --> "+inName
			# the inName file was written by MQTT callback before getting here
			if args["save"] > 0:
				frame = cv2.imread(inName)
			else:
				frame = cv2.imread("discardMe.jpg")
			(h,w)=frame.shape[:2]
			DISPLAY_DIMS=(w,h)
			image_for_result = frame.copy()
			frame = cv2.resize(frame, PREPROCESS_DIMS)
			if args["display"] == 2:
				cv2.imshow("AI Input", frame)
				key = cv2.waitKey(1) & 0xFF

			# use the NCS to acquire predictions, deceptively simple
			# all the hard AI work was done training the model used
			# and "compiling" it for the NCS on a desktop computer
			person_found = False
			predictions = predict(frame, graph)

			# loop over our predictions
			for (i, pred) in enumerate(predictions):
				# extract prediction data for readability
				(pred_class, pred_conf, pred_boxpts) = pred

				# filter out weak detections by ensuring the `confidence`
				# is greater than the minimum confidence
				if pred_conf > args["confidence"]:
					# print prediction to terminal
					#print("[INFO] Prediction #{}: class={}, confidence={}, ""boxpoints={}".format(i, CLASSES[pred_class], pred_conf, pred_boxpts))

					# build a label consisting of the predicted class and associated probability
					label = "{}: {:.0f}%".format(CLASSES[pred_class],pred_conf * 100)

					# extract information from the prediction boxpoints
					X_MULTIPLIER = float(DISPLAY_DIMS[0]) / PREPROCESS_DIMS[0]
					Y_MULTIPLIER = float(DISPLAY_DIMS[1]) / PREPROCESS_DIMS[1]
					(ptA, ptB) = (pred_boxpts[0], pred_boxpts[1])
					startX = int(ptA[0] * X_MULTIPLIER)
					startY = int(ptA[1] * Y_MULTIPLIER)
					endX = int(ptB[0] * X_MULTIPLIER)
					endY = int(ptB[1] * Y_MULTIPLIER)
					y = startY - 5 if startY - 5 > 5 else startY + 5

					# display the rectangle and label text
					cv2.rectangle(image_for_result, (startX,startY), (endX,endY), COLORS[pred_class], 1)
					cv2.putText(image_for_result, label, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[pred_class], 1)
					if pred_class == 15:
						person_found = True

			# if a person is found save the output image
			if person_found == True:
				outName=inName
				outName=outName.replace(".jpg",".out.jpg")
				cv2.imwrite(outName, image_for_result)
				#print "    Person --> "+outName	# todo: make loggile of results or output via MQTT message Topic: AI/detect perhaps
				# pass the result on to anyone that cares via MQTT
				client.publish("AI/Detect/Person", outName)  # the topic higherarchy perhaps needs more though but keep it simple to start
			#else:
			#	print "    No Detection"
		
			# check if we should display the frame on the screen
			# with prediction data (you can achieve faster FPS if you
			# do not output to the screen)
			if args["display"] > 0:
				# display the detected frame to the screen
				if person_found == True:
					cv2.imshow("Detector Output", image_for_result)
		
		# end of if len(inName) >= len(ftpdPath):  statement,  I sure do hate Python's significant whitespace feature!
		if args["display"] > 0:
			key = cv2.waitKey(1) & 0xFF	# required to pump CV2 event loop and actually display the image
			# if the `q` key was pressed, break from the loop
			if key == ord("q"):
				break
		inName=""
		#pump MQTT to get a file path of next image to be processed
		client.loop()
	
	# if "ctrl+c" is pressed in the terminal, break from the loop
	except KeyboardInterrupt:
		break

	# if there's a problem reading a frame, break gracefully
	#except AttributeError:
	#	print "  *** Exit on Attribute Error! ***"
	#	break
	except cv2.error as e:
		print inName+" --> Error!"
		print "**** openCV error:  "+str(e)
		continue	# try to soldier on, I've so far never hit this

# destroy all windows if we are displaying them
if args["display"] > 0:
	cv2.destroyAllWindows()

#delete last input file if original images are not being saved
if args["save"] == 0 and os.path.exists("discardMe.jpg"):
	os.remove("discardMe.jpg")
# clean up the graph and device
graph.DeallocateGraph()
device.CloseDevice()

# clean up MQTT
client.publish("AI/Status", "AI stopped.", 2, True)
client.loop()
client.loop()
#client.wait_for_publish()	# make sure last messagses are sent  don't exist anymore??
client.disconnect()			# normal exit, Will message should not be sent.


