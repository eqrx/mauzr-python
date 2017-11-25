""" Common image operations. """

import cv2 # pylint: disable=import-error

def rotate(**kwargs):
    """ Rotate an image. """

    flip = {None: None,
            90: cv2.ROTATE_90_CLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_COUNTERCLOCKWISE}[kwargs.get("rotate", None)]
    if flip is not None:
        return lambda i: cv2.rotate(i, flip)

def resize(**kwargs):
    """ Resize an image. """

    resolution = kwargs.get("resize", None)
    if resolution:
        return lambda i: cv2.resize(i, resolution)

def encode(**kwargs):
    """ Encode an image. """

    encoding = kwargs.get("encode", None)
    if encoding:
        return lambda i: cv2.imencode('.jpg', i)[1]

def stamp(**kwargs):
    """ Add timestamp to image. """

    import datetime
    if kwargs.get("stamp", None):
        return lambda i: cv2.putText(i, str(datetime.datetime.now()), (10, 30),
                                     cv2.FONT_HERSHEY_SIMPLEX, 1,
                                     (255, 0, 0), 3, cv2.LINE_AA)

def load_all(**kwargs):
    """ Try to load all operations. """

    ops = (rotate, resize, stamp, encode)
    cs = [c(**kwargs) for c in ops]
    return [c for c in cs if callable(c)]
