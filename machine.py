import typing

import numpy as np
from transitions import Machine
import pymurapi as mur
import cv2 as cv
import utils
import settings

if not settings.SIMULATOR:
    import picamera
from controllers import PID
import time


class AUV:
    """
    При старте записываем положение курса, что бы знать где берег
    """
    state = ''
    states = ['search_gate', 'go_from_gate', 'left_turn', 'right_turn', 'search_ball_green',
              'touch_ball', 'go_back', 'search_dock', 'go_to_dock', 'stop', 'search_ball_red',
              'search_ball_yellow', 'go_to_ball', 'turn_back', 'forward']

    def update_image(self):
        if settings.SIMULATOR:
            image = self.auv.get_image_front()
        else:
            with picamera.PiCamera() as camera:
                camera.resolution = (320, 240)
                camera.framerate = 24
                image = np.empty((240, 320, 3), dtype=np.uint8)
                camera.capture(image, 'rgb')

        self.rgb_image = image
        self.hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV)
        return image

    def __init__(self):
        self.auv = mur.mur_init()

        # курс при старте робота, в противоположном направлении берег
        self.origin = self.get_yaw()

        self.red_mask = utils.get_mask(settings.RED_RANGE)
        self.blue_mask = utils.get_mask(settings.BLUE_RANGE)
        self.green_mask = utils.get_mask(settings.GREEN_RANGE)
        self.yellow_mask = utils.get_mask(settings.YELLOW_RANGE)
        if settings.SIMULATOR:
            self.yaw_controller = PID(p=0.3, s=20)
            self.speed_controller = PID(p=1, s=20)
        else:
            self.yaw_controller = PID(p=0.3, s=40)
            self.speed_controller = PID(p=0.5, s=50)

        self.speed_error = 0
        # camera resolution
        self.resolution = self.update_image().shape
        self.left = 0
        self.right = 0
        self.contours = []

        self.start = None
        self.sub_task = False
        self.task_start_position = None

        self.machine = Machine(model=self, states=AUV.states, initial='go_from_gate')
        # после перехода очищаем словарь с маркерами
        self.machine.add_transition(
            trigger='find', source='search_gate', dest='go_from_gate', after='clear_yellow_context'
        )
        self.machine.add_transition(
            trigger='arrived', source='go_from_gate', dest='turn_back', before='save_yaw'
        )
        self.machine.add_transition(
            trigger='next', source='turn_back', dest='forward', before='save_yaw'
        )
        self.machine.add_transition(
            trigger='next', source='forward', dest='stop', before='save_yaw'
        )
        # self.machine.add_transition(
        #     trigger='arrived', source='left_turn', dest='go_from_gate'
        # )

        self.yellow_markers = {}
        self.turn_start = 0

    def update_contours(self, mask: typing.Callable):
        contours, _ = cv.findContours(mask(self.hsv_image), cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)
        new_contours = []
        for contour in contours:
            if contour.size < settings.CONTOURS_SENSITIVE:
                continue
            new_contours.append(contour)
        self.contours = new_contours

    def get_max_cnt(self):
        max_cnt = [0, None]
        c = []
        for c in self.contours:
            if c.size > max_cnt[0]:
                max_cnt[0] = c.size
                max_cnt[1] = c
        return c

    def get_yaw(self):
        """
        возвращает курс в градусах
        """
        yaw = self.auv.get_yaw()
        # if yaw < 0:
        #     yaw = 360 + yaw
        return yaw

    def calculate(self):
        self.update_image()
        getattr(self, self.state)()

        self.left = self.yaw_controller.output + self.speed_controller.output
        self.right = -self.yaw_controller.output + self.speed_controller.output

        if self.left > 100:
            self.left = 100
        elif self.left < -100:
            self.left = -100

        if self.right > 100:
            self.right = 100
        elif self.right < -100:
            self.right = -100
        if settings.SIMULATOR:
            self.auv.set_motor_power(0, self.left)
            self.auv.set_motor_power(1, self.right)
        else:
            self.auv.set_motor_power(1, self.left)
            self.auv.set_motor_power(2, self.right)

    def clear_yellow_context(self):
        self.yellow_markers = {}

    def search_same_contours(self):
        if len(self.contours) < 2:
            return []

        contours_size = [i.size for i in self.contours]
        same = []

        for i, size in enumerate(contours_size, start=1):
            size_min = size - size / 100 * settings.CONTOURS_EPSILON_PERCENT
            size_max = size + size / 100 * settings.CONTOURS_EPSILON_PERCENT
            eq_contours = []
            for j, eq_size in enumerate(contours_size[i:]):
                if size_min <= eq_size <= size_max:
                    eq_contours.append(self.contours[i + j])
            if len(eq_contours) > 0:
                eq_contours.insert(0, self.contours[i - 1])
                same.append(eq_contours)

        return same

    def search_gate(self):
        """
        Ищем пару желтых буев примерно одинакового размера, нам нужен курс до центра между ними
        """
        # self.yaw_controller.update(100)
        self.update_contours(self.yellow_mask)

        sames = self.search_same_contours()
        print('countours: {}, {}'.format(len(self.contours), len(sames)))
        for contours in sames:
            if len(contours) == 2:
                print('next')
                # нашли контуры двух дуев одинакового размера
                self.left = 0
                self.right = 0
                self.find()

    @staticmethod
    def clamp_to_360(angle):
        if angle < 0.0:
            return angle + 360.0
        if angle > 360.0:
            return angle - 360.0
        return angle

    @staticmethod
    def to_180(angle):
        if angle > 180.0:
            return angle - 360.0
        return angle

    def go_from_gate(self):
        """
        будем плыть до тех пор пока синий или зеленый маркер не станут достаточно крупными
        """
        self.update_contours(self.blue_mask)

        print('len: {}'.format(len(self.contours)))
        if self.contours is None:
            # контуры были потеряны
            pass

        for contour in self.contours:
            moments = cv.moments(contour)
            try:
                x = moments['m10'] / moments['m00']
                break
            except ZeroDivisionError:
                continue
        else:
            return

        yaw_error = self.resolution[1] / 2 - x
        print('yaw error: {}'.format(yaw_error))
        self.yaw_controller.update(yaw_error)
        # hold position
        TARGET_SIZE = 300
        speed_error = contour.size - TARGET_SIZE
        self.speed_error = speed_error
        self.speed_controller.update(speed_error)

        if abs(speed_error) < 10:
            self.arrived()

    def save_yaw(self):
        self.turn_start = self.get_yaw()

    def left_turn(self):
        if self.start is None:
            self.start = time.time()
        task_time = time.time() - self.start

        # поворачиваем на 90 градусов
        if not self.sub_task:
            print('turn')
            yaw_error = self.get_yaw() + (self.turn_start - 90)
            self.yaw_controller.update(yaw_error)

        # если повернули то движемся по кругу
        if abs(yaw_error) < 5 and task_time > 5:
            print('done task')
            self.sub_task = True
            self.start = None
        print('yaw error: {:.2f}, time:{:.2f}'.format(abs(yaw_error), task_time))

        # условие для движения после поворота на 90 градусов
        if self.sub_task and self.start is None:
            self.start = time.time()

        if self.sub_task:
            task_time = time.time() - self.start

            self.right = 40
            self.left = -40

        print('error: {:.2f}'.format(abs(self.turn_start - self.get_yaw())))
        if task_time > 10 and abs(self.turn_start - self.get_yaw()) < 5:
            self.start = None
            self.arrived()

        self.speed_controller.update(0)
        self.yaw_controller.update(0)

    def turn_back(self):

        if self.start is None:
            self.start = time.time()
        task_time = time.time() - self.start
        yaw_error = self.get_yaw() + self.turn_start
        if abs(yaw_error) < 5 and task_time > 30:
            self.start = None
            self.next()
        self.yaw_controller.update(yaw_error)

    def forward(self):
        print('forward')
        if self.start is None:
            self.start = time.time()

        task_time = time.time() - self.start

        if task_time > 30:
            self.next()

        p = self.get_yaw()
        error = self.clamp_to_360(p - self.origin)
        if abs(error) > 180:
            error *= -1
        error = self.to_180(error)
        print('error: {:.2f}, position: {:.2f}, origin:{:.2f}'.format(error, self.to_360(self.get_yaw()),
                                                                      self.to_360(self.origin)))
        self.yaw_controller.update(-1 * error)

        self.speed_controller.update(0 - 70)

    def right_turn(self):
        if self.start is None:
            self.start = time.time()

        task_time = time.time() - self.start

        self.right = 40
        self.left = -40

        print('error: {:2.f}'.format(abs(self.turn_start - self.get_yaw())))
        if task_time > 10 and abs(self.turn_start - self.get_yaw()) < 5:
            self.arrived()

        self.speed_controller.update(0)
        self.yaw_controller.update(0)

    def search_ball(self):
        pass

    def touch_ball(self):
        pass

    def go_back(self):
        pass

    @staticmethod
    def to_360(angle):
        if angle > 0.0:
            return angle
        if angle <= 0.0:
            return 360.0 + angle

    def search_dock(self):
        p = self.get_yaw()
        error = self.clamp_to_360(p - self.origin)
        if abs(error) > 180:
            error *= -1
        error = self.to_180(error)
        print('error: {:.2f}, position: {:.2f}, origin:{:.2f}'.format(error, self.to_360(self.get_yaw()),
                                                                      self.to_360(self.origin)))
        self.yaw_controller.update(-1 * error)
        speed = 70
        # self.speed_controller.update(0 - speed)
        print('speed l:{:.2f}, r:{:.2f}'.format(self.left, self.right))

    def go_dock(self):
        pass

    def stop(self):
        pass

    def execute_task(self):
        print(self.state)
