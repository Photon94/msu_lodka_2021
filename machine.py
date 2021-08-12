import typing

import numpy as np
from transitions import Machine
import pymurapi as mur
import cv2 as cv
import utils
import settings
from controllers import PID


class AUV:
    """
    При старте записываем положение курса, что бы знать где берег
    """
    state = ''
    states = ['search_gate', 'go_from_gate', 'left_turn', 'right_turn', 'search_ball_green',
              'touch_ball', 'go_back', 'search_dock', 'go_to_dock', 'stop', 'search_ball_red',
              'search_ball_yellow', 'go_to_ball']

    def update_image(self):
        image = self.auv.get_image_front()
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

        self.yaw_controller = PID(p=0.1)
        self.speed_controller = PID(p=0.1)

        self.speed_error = 0
        # camera resolution
        self.resolution = self.update_image().shape
        self.left = 0
        self.right = 0
        self.contours = []

        self.machine = Machine(model=self, states=AUV.states, initial='search_gate')
        # после перехода очищаем словарь с маркерами
        self.machine.add_transition(
            trigger='find', source='search_gate', dest='go_from_gate', after='clear_yellow_context'
        )
        self.machine.add_transition(
            trigger='arrived', source='go_from_gate', dest='left_turn', before='save_yaw'
        )
        # example
        self.machine.add_transition(
            trigger='arrived', source='go_from_gate', dest='right_turn'
        )
        self.machine.add_transition(
            trigger='done_turn', source='right_turn', dest='search_gate'
        )
        self.machine.add_transition(
            trigger='find', source='search_gate', dest='go_from_gate'
        )
        self.machine.add_transition(
            trigger='lost', source='go_to_task', dest='search_task'
        )
        self.machine.add_transition(
            trigger='arrived', source='go_from_gate', dest='left_turn'
        )
        self.machine.add_transition(
            trigger='done_turn', source='left_turn', dest='search_ball_red'
        )
        self.machine.add_transition(
            trigger='done_turn', source='search_ball_red', dest='go_to_ball'
        )
        self.machine.add_transition(
            trigger='done_turn', source='go_to_ball', dest='search_ball_yellow'
        )
        self.machine.add_transition(
            trigger='done_turn', source='search_ball_yellow', dest='go_to_ball'
        )
        self.machine.add_transition(
            trigger='done_turn', source='go_to_ball', dest='search_ball_green'
        )
        self.machine.add_transition(
            trigger='done_turn', source='search_ball_green', dest='go_to_ball'
        )
        self.machine.add_transition(
            trigger='done_turn', source='go_to_ball', dest='search_dock'
        )
        self.machine.add_transition(
            trigger='done_turn', source='search_dock', dest='go_to_dock'
        )
        self.machine.add_transition(
            trigger='done_turn', source='go_to_dock', dest='stop'
        )

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
        if yaw < 0:
            yaw = 180 - yaw
        return yaw

    def calculate(self):
        self.update_image()
        getattr(self, self.state)()

        self.left = self.yaw_controller.output + self.speed_controller.output
        self.right = -self.yaw_controller.output + self.speed_controller.output

        self.auv.set_motor_power(0, self.left)
        self.auv.set_motor_power(1, self.right)

    def clear_yellow_context(self):
        self.yellow_markers = {}

    def search_same_contours(self) -> [[np.ndarray]]:
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

        for contours in sames:
            if len(contours) == 2:
                # нашли контуры двух дуев одинакового размера
                self.left = 0
                self.right = 0
                self.find()

    def go_from_gate(self):
        """
        будем плыть до тех пор пока синий или зеленый маркер не станут достаточно крупными
        """
        self.update_contours(self.green_mask)
        if self.contours is None:
            # контуры были потеряны
            pass

        for contour in self.contours:
            moments = cv.moments(contour)
            try:
                x = moments['m10']/moments['m00']
                break
            except ZeroDivisionError:
                continue
        else:
            return

        yaw_error = self.resolution[1] / 2 - x
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
        yaw_error = self.get_yaw() + (self.turn_start - 90)
        self.yaw_controller.update(yaw_error)

    def right_turn(self):
        pass

    def search_ball(self):
        pass

    def touch_ball(self):
        pass

    def go_back(self):
        pass

    def search_dock(self):
        pass

    def go_dock(self):
        pass

    def stop(self):
        pass

    def execute_task(self):
        print(self.state)
