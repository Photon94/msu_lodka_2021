import typing
from collections import namedtuple
import numpy
import cv2 as cv


Range = namedtuple('Range', ['low', 'high'])


def get_mask(color_ranges: typing.Union[typing.List[Range], Range] = None) -> typing.Callable:
    def mask(image: numpy.ndarray) -> numpy.ndarray:
        nonlocal color_ranges
        if not isinstance(color_ranges, list):
            color_ranges = [color_ranges]
        masks = []
        for color_range in color_ranges:
            masks.append(
                cv.inRange(image, color_range.low, color_range.high)
            )
        return sum(masks)
    return mask






