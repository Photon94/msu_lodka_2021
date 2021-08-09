import machine
import cv2 as cv

auv = machine.AUV()
font = cv.FONT_HERSHEY_COMPLEX_SMALL

while True:

    cv.imshow('', auv.rgb_image)
    cv.waitKey(1)

    t_color = (255, 128, 255)
    c_color = (0, 255, 0)
    x_center = int(auv.resolution[1] / 2)
    # vertical line in center of screen
    cv.line(auv.rgb_image, (x_center, 0), (x_center, auv.resolution[0]), (128, 128, 128), 1)
    cv.putText(auv.rgb_image, auv.state, (5, 20), font, 0.5, t_color, 1, cv.LINE_AA)
    # cv.putText(image, 'e:' + '{:.2f}'.format(e_x), (5, 40), font, 0.5, t_color, 1, cv.LINE_AA)
    cv.putText(auv.rgb_image, 'u:' + '{:.2f}/{:.2f}'.format(auv.left, auv.right), (5, 60), font, 0.5, t_color, 1, cv.LINE_AA)
    # cv.putText(image, 's:' + str(area), (5, 80), font, 0.5, t_color, 1, cv.LINE_AA)
    cv.drawContours(auv.rgb_image, auv.contours, -1, c_color, 2)

    auv.calculate()

