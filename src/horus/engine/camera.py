#!/usr/bin/python
# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------#
#                                                                       #
# This file is part of the Horus Project                                #
#                                                                       #
# Copyright (C) 2014-2015 Mundo Reader S.L.                             #
#                                                                       #
# Date: March, Octobrer 2014                                            #
# Author: Jesús Arroyo Torrens <jesus.arroyo@bq.com>                    #
#                                                                       #
# This program is free software: you can redistribute it and/or modify  #
# it under the terms of the GNU General Public License as published by  #
# the Free Software Foundation, either version 2 of the License, or     #
# (at your option) any later version.                                   #
#                                                                       #
# This program is distributed in the hope that it will be useful,       #
# but WITHOUT ANY WARRANTY; without even the implied warranty of        #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the          #
# GNU General Public License for more details.                          #
#                                                                       #
# You should have received a copy of the GNU General Public License     #
# along with this program. If not, see <http://www.gnu.org/licenses/>.  #
#                                                                       #
#-----------------------------------------------------------------------#

__author__ = "Jesús Arroyo Torrens <jesus.arroyo@bq.com>"
__license__ = "GNU General Public License v2 http://www.gnu.org/licenses/gpl.html"

import cv2
import math
import time
import platform

from ..hardware import uvc_capture as uvc


class Error(Exception):
	def __init__(self, msg):
		self.msg = msg
	def __str__(self):
		return repr(self.msg)

class CameraNotConnected(Error):
	def __init__(self, msg="CameraNotConnected"):
		super(CameraNotConnected, self).__init__(msg)

class WrongCamera(Error):
	def __init__(self, msg="WrongCamera"):
		super(WrongCamera, self).__init__(msg)

class InvalidVideo(Error):
	def __init__(self, msg="InvalidVideo"):
		super(InvalidVideo, self).__init__(msg)


class Camera:
	""" """
	def __init__(self, parent=None, cameraId=0):
		self.parent = parent
		self.cameraId = cameraId

		self.capture = None
		self.isConnected = False

		self.reading = False

		self.framerate = 30
		self.width = 800
		self.height = 600
		self.useDistortion = False

		self.cameraMatrix = None
		self.distortionVector = None
		self.distCameraMatrix = None

		if platform.system() == 'Windows':
			self.maxBrightness = 1.
			self.maxContrast = 1.
			self.maxSaturation = 1.
		else:
			self.maxBrightness = 255.
			self.maxContrast = 255.
			self.maxSaturation = 255.
			self.maxExposure = 1000.

		self.unplugCallback = None
		self._n = 0 # Check if command fails

	def setCameraId(self, cameraId):
		self.cameraId = cameraId

	def setUnplugCallback(self, unplugCallback=None):
		self.unplugCallback = unplugCallback

	def connect(self):
		print ">>> Connecting camera {0}".format(self.cameraId)
		self.isConnected = False
		if self.capture is not None:
			self.capture.close()
		
		self.capture = uvc.autoCreateCapture(self.cameraId,(self.width,self.height))
		self.capture.controls['UVCC_REQ_EXPOSURE_AUTOMODE'].set_val(0);
		self.capture.controls['UVCC_REQ_EXPOSURE_AUTOPRIO'].set_val(0);
		
		
		
		time.sleep(0.2)
		
		if self.capture is not None:
			print ">>> Done"
			self.isConnected = True
			self.checkVideo()
			self.checkCamera()
		else:
			raise CameraNotConnected()
		
	def disconnect(self):
		tries = 0
		if self.isConnected:
			print ">>> Disconnecting camera {0}".format(self.cameraId)
			if self.capture is not None:
				self.capture.close();
				print ">>> Done"
				

	def checkCamera(self):
		""" Checks correct camera """
		print "Exposure {0}".format(self.capture.controls['UVCC_REQ_EXPOSURE_ABS'].get_val())
		self.setExposure(2)
		print "Exposure {0}".format(self.capture.controls['UVCC_REQ_EXPOSURE_ABS'].get_val())
		exposure = self.getExposure()
		if exposure is not None:
			if exposure < 1:
				raise WrongCamera()

	def checkVideo(self):
		""" Checks correct video """
		if self.captureImage() is None or (self.captureImage()==0).all():
			raise InvalidVideo()

	def captureImage(self, mirror=False, flush=False, flushValue=1):
		""" If mirror is set to True, the image will be displayed as a mirror,
		otherwise it will be displayed as the camera sees it """
		if self.isConnected:
			self.reading = True

			#if flush:
			#	for i in range(0, flushValue):
			#		self.capture.read() #grab()

			ret = self.capture.get_frame();
			if (ret is not None):
				image=ret.img
				
			self.reading = False
			if ret:
				if self.useDistortion and \
				   self.cameraMatrix is not None and \
				   self.distortionVector is not None and \
				   self.distCameraMatrix is not None:
					mapx, mapy = cv2.initUndistortRectifyMap(self.cameraMatrix, self.distortionVector,
															 R=None, newCameraMatrix=self.distCameraMatrix,
															 size=(self.width, self.height), m1type=5)
					image = cv2.remap(image, mapx, mapy, cv2.INTER_LINEAR)
				image = cv2.transpose(image)
				if not mirror:
					image = cv2.flip(image, 1)
				self._success()
				return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
			else:
				self._fail()
				return None
		else:
			self._fail()
			return None

	def _success(self):
		self._n = 0

	def _fail(self):
		self._n += 1
		if self._n >= 3:
			self._n = 0
			if self.unplugCallback is not None and \
			   self.parent is not None and not self.parent.unplugged:
				self.parent.unplugged = True
				self.unplugCallback()

	def getResolution(self):
		return int(self.height), int(self.width) #-- Inverted values because of transpose

	def setBrightness(self, value):
		if self.isConnected:
			value = int(value)/self.maxBrightness
			self.capture.controls['UVCC_REQ_BRIGHTNESS_ABS'].set_val(int(value))
			#self.capture.set(cv2.cv.CV_CAP_PROP_BRIGHTNESS, value)

	def setContrast(self, value):
		if self.isConnected:
			value = int(value)/self.maxContrast
			
			self.capture.controls['UVCC_REQ_CONTRAST_ABS'].set_val(int(value))
			
			#self.capture.set(cv2.cv.CV_CAP_PROP_CONTRAST, value)

	def setSaturation(self, value):
		if self.isConnected:
			value = int(value)/self.maxSaturation
			self.capture.controls['UVCC_REQ_SATURATION_ABS'].set_val(int(value))
			#self.capture.set(cv2.cv.CV_CAP_PROP_SATURATION, value)

	def setExposure(self, value):
		if self.isConnected:
			if platform.system() == 'Windows':
				value = int(round(-math.log(value)/math.log(2)))
			elif platform.system() == 'Darwin':
				value = int(value)
			else:
				value = int(value) / self.maxExposure
			
			print "Exposure REQUESTED {0}".format(value)	
			self.capture.controls['UVCC_REQ_EXPOSURE_ABS'].set_val(value)
			#self.capture.set(cv2.cv.CV_CAP_PROP_EXPOSURE, value)

	def setFrameRate(self, value):
		if self.isConnected:
			self.capture.set_fps(value)
			#self.capture.set(cv2.cv.CV_CAP_PROP_FPS, value)

	def _setWidth(self, value):
		if self.isConnected:
			(w,h)= self.capture.get_size()
			self.capture.set_size((value,h))

	def _setHeight(self, value):
		if self.isConnected:
			(w,h)= self.capture.get_size()
			self.capture.set_size((w,value))
			#self.capture.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, value)	

	def _updateResolution(self):
		if self.isConnected:
			(w,h)= self.capture.get_size()
			self.width=w
			self.height=h
			#self.width = int(self.capture.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
			#self.height = int(self.capture.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))

	def setResolution(self, width, height):
		self._setWidth(width)
		self._setHeight(height)
		self._updateResolution()

	def setUseDistortion(self, value):
		self.useDistortion = value

	def setIntrinsics(self, cameraMatrix, distortionVector):
		self.cameraMatrix = cameraMatrix
		self.distortionVector = distortionVector
		self.distCameraMatrix = cv2.getOptimalNewCameraMatrix(self.cameraMatrix, self.distortionVector, (int(self.width),int(self.height)), alpha=1)[0]

	def getExposure(self):
		if self.isConnected:
			#value = self.capture.get(cv2.cv.CV_CAP_PROP_EXPOSURE)
			value = self.capture.controls['UVCC_REQ_EXPOSURE_ABS'].get_val()
			
			if platform.system() == 'Windows':
				value = 2**-value
			elif platform.system() == 'Darwin':
				pass
			else:
				value *= self.maxExposure
			return value