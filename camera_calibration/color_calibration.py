import typing
import cv2
import numpy as np
from transitions import Machine
import pymurapi as mur
import utils
import settings

from controllers import PID
import time
# from utils import Range
#
#
# BLUE_RANGE = Range(low=(100, 90, 100), high=(100, 120, 120))
# image = cv2.imread('examples/start_position.jpg')
# gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
# hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
#
# sobx = cv2.createImage(cv2.GetSize(image), cv2.IPL_DEPTH_16S, 1)
# cv2.Sobel(image, sobx, 1, 0, 3) #Sobel with x-order=1
#
# soby = cv2.CreateImage(cv2.GetSize(image), cv2.IPL_DEPTH_16S, 1)
# cv2.Sobel(image, soby, 0, 1, 3) #Sobel withy-oder=1
#
# cv2.Abs(sobx, sobx)
# cv2.Abs(soby, soby)
#
# result = cv2.CloneImage(image)
# cv2.Add(sobx, soby, result) #Add the two results together.
#
# cv2.Threshold(result, result, 100, 255, cv2.CV_THRESH_BINARY_INV)
#
#
# blur = cv.GaussianBlur(gray,(5,5),0)
# t, p = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
# cv.imwrite('blue_contour.png', result)


import cv2
import numpy as np
from matplotlib import pyplot as plt

# loading image
#img0 = cv2.imread('SanFrancisco.jpg',)
img0 = cv2.imread('examples/start_position.jpg',)

# converting to gray scale
gray = cv2.cvtColor(img0, cv2.COLOR_BGR2GRAY)

# remove noise
img = cv2.GaussianBlur(gray,(3,3),0)

# convolute with proper kernels
laplacian = cv2.Laplacian(img,cv2.CV_64F)
sobelx = cv2.Sobel(img,cv2.CV_64F,1,0,ksize=3)  # x
sobely = cv2.Sobel(img,cv2.CV_64F,0,1,ksize=3)  # y

plt.subplot(2,2,1),plt.imshow(img,cmap = 'gray')
plt.title('Original'), plt.xticks([]), plt.yticks([])
plt.subplot(2,2,2),plt.imshow(laplacian,cmap = 'gray')
plt.title('Laplacian'), plt.xticks([]), plt.yticks([])
plt.subplot(2,2,3),plt.imshow(sobelx,cmap = 'gray')
plt.title('Sobel X'), plt.xticks([]), plt.yticks([])
plt.subplot(2,2,4),plt.imshow(sobely,cmap = 'gray')
plt.title('Sobel Y'), plt.xticks([]), plt.yticks([])

plt.show()


# def update_contours(mask: typing.Callable):
#     contours, _ = cv2.findContours(mask(hsv_image), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
#     new_contours = []
#     for contour in contours:
#         if contour.size < settings.CONTOURS_SENSITIVE:
#             continue
#         new_contours.append(contour)
#     return contours
#
#
#
# c_color = (0, 255, 0)
#
# blue_mask = utils.get_mask(settings.BLUE_RANGE)
# contours = update_contours(blue_mask)
# cv.drawContours(image, contours, -1, c_color, 2)











