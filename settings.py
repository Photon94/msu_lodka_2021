from utils import Range

YELLOW_RANGE = Range(low=(15, 50, 50), high=(45, 255, 255))
RED_RANGE = [Range(low=(0, 50, 50), high=(15, 255, 255)), Range(low=(175, 50, 50), high=(180, 255, 255))]
GREEN_RANGE = Range(low=(45, 90, 90), high=(125, 255, 255))

BLUE_RANGE = Range(low=(80, 70, 70), high=(120, 255, 255))

SIMULATOR = False

# пороговое значение для определения контуров
CONTOURS_SENSITIVE = 30

# эпсилон при сравнении контуров
CONTOURS_EPSILON_PERCENT = 1

# угол обзора камеры
CAMERA_VIEWING_ANGLE = 50

