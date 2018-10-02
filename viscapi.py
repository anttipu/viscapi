#!/usr/bin/env python
import pygame
from os import environ
from pygame.locals import *
from pysca import pysca
from numpy import clip
import threading
from subprocess import call

JOYSTICKS = []
axis_x_value = 0.0
axis_y_value = 0.0
axis_z_value = 0.0
throttle_y_value = 0.0
hat_y_value = 0
hat_x_value = 0
buttons_value = [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ]

joystic_thread = None
joystic_thread_alive = False

state_read_lock = threading.Condition()

def joystick_thread_runner():
    # TODO Handle the "close" command gracefully
    while (joystic_thread_alive):
        event = pygame.event.wait()
        proc_event(event)

def proc_event(event):
    global axis_x_value
    global axis_y_value
    global axis_z_value
    global hat_y_value
    global hat_x_value
    global throttle_y_value
    global buttons_value
    global joystic_thread_alive

    with state_read_lock:
        if event.type == QUIT:
            joystic_thread_alive = False
            print("Received event 'Quit', exiting.")
            exit(0)
        elif event.type == JOYAXISMOTION:
            if event.axis == 0:
                axis_x_value = event.value
            elif event.axis == 1:
                axis_y_value = event.value
            elif event.axis == 2:
                axis_z_value = event.value
            elif event.axis == 3:
                throttle_y_value = (event.value * -1) + 1
        elif event.type == JOYBUTTONDOWN:
            buttons_value[int(event.button)] = 1;
        elif event.type == JOYBUTTONUP:
            buttons_value[int(event.button)] = 0;
        elif event.type == JOYHATMOTION:
            hat_y_value = event.value[1]
            hat_x_value = event.value[0]

    # Very crude but somwhat working solution to kill the program
    # if serial communication hangs for some reason
    if buttons_value[7] == 1 and buttons_value[9] == 1:
        print 'Ending program'
        call(["killall", "-9", "python"])

def value_change(prev_axis_x, prev_axis_y, prev_axis_z, prev_throttle_y, prev_hat_x, prev_hat_y, prev_buttons):
    global axis_x_value
    global axis_y_value
    global axis_z_value
    global hat_y_value
    global hat_x_value
    global throttle_y_value
    global buttons_value

    if (prev_axis_x != axis_x_value or prev_axis_y != axis_y_value or
        prev_axis_z != axis_z_value or prev_hat_x != hat_x_value or
        prev_hat_y != hat_y_value or prev_throttle_y != throttle_y_value or
        prev_buttons != buttons_value):
        return True
    return False

def main():
    global axis_x_value
    global axis_y_value
    global axis_z_value
    global hat_y_value
    global hat_x_value
    global throttle_y_value
    global buttons_value
    global joystic_thread_alive

    prev_axis_x = -1.0
    prev_axis_y =  -1.0
    prev_axis_z = -1.0
    prev_hat_y = -1
    prev_hat_x = -1
    prev_throttle_y = -1.0
    prev_buttons = [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ]

    environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    pygame.display.set_mode((0,0),pygame.FULLSCREEN)
    pysca.connect('/dev/ttyUSB0')
    pysca.set_power_on(1, True)
    clock = pygame.time.Clock()
    pysca.set_wb_mode(1, "auto", blocking=True)
    pysca.set_focus_mode(1, "auto", blocking=True)
    prev_zoom = 1
    zoom_mode = "stop"
    wb_mode = "auto"
    focus_mode = "auto"
    focus_action = "stop"
    twist_zoom = False
    tilt_invert = -1

    for i in range(0, pygame.joystick.get_count()):
        JOYSTICKS.append(pygame.joystick.Joystick(i))
        JOYSTICKS[-1].init()

    joystic_thread_alive = True
    joystic_thread = threading.Thread(target=joystick_thread_runner, name="joystick-reader-thread")
    joystic_thread.start()

    while joystic_thread_alive:
        try:
            clock.tick(10)

            with state_read_lock:
                value_changed = value_change(prev_axis_x, prev_axis_y, prev_axis_z, prev_throttle_y,
                                             prev_hat_x, prev_hat_y, prev_buttons)
                axis_x = axis_x_value
                axis_y =  axis_y_value
                axis_z = axis_z_value
                hat_y = hat_y_value
                hat_x = hat_x_value
                throttle_y = throttle_y_value
                buttons = list(buttons_value)

            if not value_changed:
                continue

            pan_multiplier = 1 + throttle_y * 10
            tilt_multiplier = 1 + throttle_y * 13
            zoom_multiplier = 1 + throttle_y * 3
            twist_zoom_multiplier = throttle_y * 2.5

            pan = clip(int(pan_multiplier * axis_x), -24, 24)
            tilt = tilt_invert * clip(int(tilt_multiplier * axis_y), -18, 18)

            zoom = 0
            if twist_zoom == True and axis_z != 0.0:
                if axis_z < 0:
                    twist_zoom_value = axis_z - 1.0
                else:
                    twist_zoom_value = axis_z + 1.0
                zoom = clip(int(twist_zoom_value + (twist_zoom_multiplier * axis_z)), -7, 7)
            if zoom == 0:
                zoom = clip(int(zoom_multiplier * hat_y), -7, 7)

#            print("X: %0.3f, Y: %0.3f, Z:%0.3f, T:%0.3f pan: %s (0x%02x), tilt: %s (0x%02x), zoom: %s (0x%02x), buttons: %s" % (axis_x, axis_y, axis_z, throttle_y, pan, pan, tilt, tilt, zoom, zoom, buttons))

            any_button_pressed = False
            for i in xrange(len(buttons)):
                if buttons[i] != 0:
                    any_button_pressed = True
                    break

            if any_button_pressed == False:
                pysca.pan_tilt(1, pan=pan, tilt=tilt, blocking=True)

            if buttons[10] == 1:
                if buttons[2] == 1:
                    pysca.set_memory(1, 0, blocking=True)
                elif buttons[3] == 1:
                    pysca.set_memory(1, 1, blocking=True)
                elif buttons[4] == 1:
                    pysca.set_memory(1, 2, blocking=True)
                elif buttons[5] == 1:
                    pysca.set_memory(1, 3, blocking=True)
            else:
                if buttons[2] == 1:
                    pysca.recall_memory(1, 0, blocking=True)
                elif buttons[3] == 1:
                    pysca.recall_memory(1, 1, blocking=True)
                elif buttons[4] == 1:
                    pysca.recall_memory(1, 2, blocking=True)
                elif buttons[5] == 1:
                    pysca.recall_memory(1, 3, blocking=True)

            if buttons[0] == 1:
                if focus_mode != "auto":
                    pysca.set_focus_mode(1, "auto", blocking=True)
                    focus_mode = "auto"
                pysca.set_focus_mode(1, "trigger", blocking=True)

            if buttons[1] == 1:
                if wb_mode != "auto":
                    pysca.set_wb_mode(1, "auto", blocking=True)
                    wb_mode = "auto"

            if buttons[11] == 1:
                if wb_mode != "manual":
                    pysca.set_wb_mode(1, "manual", blocking=True)
                    wb_mode = "manual"

                if hat_x > 0:
                    pysca.set_red_gain(1, "up", blocking=True)
                elif hat_x < 0:
                    pysca.set_red_gain(1, "down", blocking=True)
                if hat_y > 0:
                    pysca.set_blue_gain(1, "up", blocking=True)
                elif hat_y < 0:
                    pysca.set_blue_gain(1, "down", blocking=True)
            else:
                if zoom < 0 and (zoom_mode != "wide" or prev_zoom != zoom):
                    pysca.zoom(1, "wide", speed=-1*(zoom-1), blocking=True)
                    zoom_mode = "wide"
                    prev_zoom = zoom
                elif zoom > 0 and (zoom_mode != "tele" or prev_zoom != zoom):
                    pysca.zoom(1, "tele", speed=zoom-1, blocking=True)
                    zoom_mode = "tele"
                    prev_zoom = zoom
                elif zoom == 0 and zoom_mode != "stop":
                    pysca.zoom(1, "stop", blocking=True)
                    zoom_mode = "stop"
                    prev_zoom = zoom

                if hat_x > 0:
                    if focus_mode != "manual":
                        pysca.set_focus_mode(1, "manual", blocking=True)
                        focus_mode = "manual"
                    if focus_action != "far":
                        pysca.focus(1, "far", speed=2, blocking=True)
                        focus_action = "far"
                elif hat_x < 0:
                    if focus_mode != "manual":
                        pysca.set_focus_mode(1, "manual", blocking=True)
                        focus_mode = "manual"
                    if focus_action != "near":
                        pysca.focus(1, "near", speed=2, blocking=True)
                        focus_action = "near"
                elif hat_x == 0 and focus_action != "stop":
                    pysca.focus(1, "stop", blocking=True)
                    focus_action = "stop"

            if buttons[6] == 1:
                twist_zoom = True
            if buttons[7] == 1:
                twist_zoom = False
            if buttons[8] == 1:
                tilt_invert = 1
            if buttons[9] == 1:
                tilt_invert = -1

            prev_axis_x = axis_x
            prev_axis_y =  axis_y
            prev_axis_z = axis_z
            prev_hat_y = hat_y
            prev_hat_x = hat_x
            prev_throttle_y = throttle_y
            prev_buttons = list(buttons)

        except KeyboardInterrupt:
            print("\n" "Interrupted")
            joystic_thread_alive = False
            exit(0)

if __name__ == "__main__":
    main()

