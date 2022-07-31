"""
This is a drawing tool to draw G-Code via a mouse pointer on screen.
"""
import _thread
import os
import threading
import time
import typing
from enum import Enum
from pynput.mouse import Controller, Button
from pynput import keyboard
import re

mouse = Controller()

# the scale of the
DRAW_SCALE = 3

# the offset for the starting position of the drawing, adjust according to G-Code
X_OFFSET = 100
Y_OFFSET = 100


class MouseMovement(typing.TypedDict):
    """
    A single mouse movement represents a single G-Code command
    """
    # whether this is a drawing move
    drawing: bool
    # the next mouse x position
    x: int
    # the next mouse y position
    y: int


class Operational(Enum):
    """
    The operational status for the drawing thread
    """
    # program does nothing
    IDLE = 0
    # program currently drawing
    RUNNING = 1
    # program started drawing
    STARTED = 2
    # program stopped drawing
    STOPPED = 3
    # program exit
    EXIT = -1


operational_status = Operational.IDLE

# exit event for the drawing thread
stop_event = threading.Event()

mouse_movements: list[MouseMovement] = []


def draw_function():
    """
    Drawing thread which monitors the operational status and starts/stops the drawing process
    """

    global operational_status
    while True:
        time.sleep(0.1)
        if operational_status == Operational.STARTED:
            mouse.press(Button.left)

            # get the start position of the drawing
            x_start_pos = mouse.position[0] - X_OFFSET
            y_start_pos = mouse.position[1] - Y_OFFSET

            operational_status = Operational.RUNNING

            # go over each mouse movement (G-Code command)
            for pos in mouse_movements:
                if operational_status == Operational.RUNNING:
                    # G0 commands are hops and should therefore not be drawn
                    if not pos['drawing']:
                        mouse.release(Button.left)
                    # G1 commands should be drawn
                    else:
                        mouse.press(Button.left)

                    # move the mouse
                    mouse.position = (
                        pos['x'] * DRAW_SCALE + x_start_pos,
                        pos['y'] * DRAW_SCALE + y_start_pos
                    )
                    time.sleep(0.005)
                else:
                    break

            # when we are finished let go of the mouse button
            mouse.release(Button.left)
            operational_status = Operational.IDLE


def set_operational_status(status: Operational):
    if status == Operational.EXIT:
        quit()

    global operational_status
    operational_status = status


if __name__ == '__main__':
    with open("fry_and_bender.gcode", "r") as gcode_file:
        lines = gcode_file.readlines()

        for command in lines:
            # G commands are movement commands (the only relevant commands here)
            # they should look something like this: "G0 X123.456 Y321.654"
            if re.search(r"G\d.*X.*Y", command):
                x_position = re.findall(r"X\d*", command)[0][1:]
                y_position = re.findall(r"Y\d*", command)[0][1:]

                mouse_movements.append({
                    "drawing": command.startswith("G1"),  # G1 commands are movements that are drawn, G0 should not draw
                    "x": int(x_position),
                    "y": int(y_position)
                })

        # the first few and last G commands are often useless
        mouse_movements = mouse_movements[2:-2]

    # prepare the keyboard listener
    with keyboard.GlobalHotKeys({
        '<ctrl>+<alt>+q': lambda: set_operational_status(Operational.STARTED),
        '<ctrl>+<alt>+w': lambda: set_operational_status(Operational.STOPPED),
        '<ctrl>+<alt>+x': lambda: set_operational_status(Operational.EXIT)
    }) as listener:
        operational_status = Operational.IDLE

        # the draw thread looks at the current status and starts/stops the drawing process
        draw_thread = threading.Thread(target=draw_function)
        draw_thread.start()

        listener.join()
