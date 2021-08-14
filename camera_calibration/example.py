import numpy as np
import cv2 as cv
import glob
# Условие прекращения
criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)
# Подготовить точки объекта, такие как (0,0,0), (1,0,0), (2,0,0) ...., (6,5,0)
objp = np.zeros((6*8,3), np.float32)
objp[:,:2] = np.mgrid[0:8,0:6].T.reshape(-1,2)
# Используется для хранения точек объекта и точек изображения всех изображений.
objpoints = [] # 3д очка в реальном мире
imgpoints = [] # 2d точки на изображении
images = glob.glob('calibration_images/*.jpg')
for fname in images:
    img = cv.imread(fname)
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    cv.imwrite('gray.png', gray)
    # Найдите угол доски
    print('ing')
    ret, corners = cv.findChessboardCorners(gray, (6,8), None)
    # Если найдено, добавить точку объекта, точку изображения (после доработки)
    if ret == True:
        objpoints.append(objp)
        corners2 = cv.cornerSubPix(gray,corners, (11,11), (-1,-1), criteria)
        imgpoints.append(corners)
        # Нарисовать и отобразить углы
        cv.drawChessboardCorners(img, (8,6), corners2, ret)
        # cv.imshow('img', img)
        # cv.waitKey(500)
        cv.imwrite('calibresult1.png', img)
        print('done')
cv.destroyAllWindows()