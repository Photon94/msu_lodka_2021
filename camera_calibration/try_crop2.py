import cv2
import utils
import settings
import typing

from sys import argv


def update_contours(mask: typing.Callable):
    contours, _ = cv2.findContours(mask(hsv_image), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    new_contours = []
    for contour in contours:
        if contour.size < settings.CONTOURS_SENSITIVE:
            continue
        new_contours.append(contour)
    return new_contours

img = cv2.imread(argv)
hsv_image = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

height, width = img.shape[:2]
crop_img = img[int(height/2):int(height - height/3), :]

c_color = (0, 255, 0)

blue_mask = utils.get_mask(settings.YELLOW_RANGE)
contours = update_contours(blue_mask)
cv2.drawContours(img, contours, -1, c_color, 2)
print(len(contours))

cv2.imshow("cropped.jpg", crop_img)
cv2.waitKey(0)



