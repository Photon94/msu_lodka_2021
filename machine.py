import typing

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
    states = ['search_gate', 'go_in_gate', 'go_out_gate', 'left_turn', 'right_turn', 'search_ball',
              'touch_ball', 'go_back', 'search_dock', 'go_dock', 'stop']

    def update_image(self):
        image = self.auv.get_image_front()
        self.rgb_image = image
        self.hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV)
        return image

    def __init__(self):
        self.auv = mur.mur_init()

        self.red_mask = utils.get_mask(settings.RED_RANGE)
        self.blue_mask = utils.get_mask(settings.BLUE_RANGE)
        self.green_mask = utils.get_mask(settings.GREEN_RANGE)
        self.yellow_mask = utils.get_mask(settings.YELLOW_RANGE)

        self.yaw_controller = PID(p=0.1)
        self.speed_controller = PID(p=0.1)

        # camera resolution
        self.resolution = self.update_image().shape
        self.left = 0
        self.right = 0
        self.contours = []

        self.machine = Machine(model=self, states=AUV.states, initial='search_task')
        self.machine.add_transition(
            trigger='find_gate', source='search_gate', dest='go_in_gate'
        )
        self.machine.add_transition(
            trigger='arrived', source='go_to_task', dest='execute_task'
        )
        self.machine.add_transition(
            trigger='lost', source='go_to_task', dest='search_task'
        )

    def update_contours(self, mask: typing.Callable):
        self.contours, _ = cv.findContours(mask(self.hsv_image), cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)

    def get_max_cnt(self):
        max_cnt = [0, None]
        c = None
        for c in self.contours:
            if c.size > max_cnt[0]:
                max_cnt[0] = c.size
                max_cnt[1] = c
        return c

    def calculate(self):
        self.update_image()
        getattr(self, self.state)()

        self.left = self.yaw_controller.output + self.speed_controller.output
        self.right = -self.yaw_controller.output + self.speed_controller.output

        self.auv.set_motor_power(0, self.left)
        self.auv.set_motor_power(1, self.right)

    def search_gate(self):
        """
        Ищем пару желтых буев примерно одинакового размера, нам нужен курс до центра между ними
        """
        self.yaw_controller.update(100)
        self.update_contours(self.yellow_mask)
        c = self.get_max_cnt()
        if c is not None:
            self.find()

    def go_in_gate(self):
        """
        плывем до буя в воротах, как ворота проподут из поле зрения и буй будет достаточно
        близок, переходим к маневру поворота по часовой стрелки или против
        или
        если мы плывем в обратном направлении то плывем до тех пор пока врата не проподут
        из виду
        """
        # ищем желтые контуры их дожно быть два примерно одинаковых размеров
        self.update_contours(self.yellow_mask)
        if self.contours is None:
            # контуры были потеряны
            pass

        for contour in self.contours:
            moments = cv.moments(contour)
            try:
                x = moments['m10']/moments['m00']
            except ZeroDivisionError:
                continue
        yaw_error = self.resolution[1] / 2 - x
        self.yaw_controller.update(yaw_error)
        # hold position
        marker_size = cnt.size
        self.speed_controller.update(marker_size - 300)

    def left_turn(self):
        pass

    def right_turn(self):
        pass

    def go_to_balls(self):
        pass

    def touch_ball(self):
        pass

    def search_ball(self):
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
