#!/usr/bin/env python2

from __future__ import division, absolute_import, unicode_literals, print_function

import copy
import os
import signal
import threading

import json
from numpy import clip
import pygame
from pysca import pysca

# JSON keywords
CONFIG_BUTTONS = 'buttons'
CONFIG_KEYS = 'keys'
CONFIG_AXES = 'axes'
CONFIG_HATS = 'hats'
CONFIG_PARAMETERS = 'parameters'
DEFAULT_LAYOUT = 'default-layout'
LAYOUT = 'layout-'
LAYOUT_BUTTON = 'layout-button'
LAYOUT_KEY = 'layout-key'

# Actions
MEMORY_SET = 'memory-set'
MEMORY_RECALL = 'memory-recall'

AUTO_FOCUS = 'auto-focus'
FOCUS_FAR = 'focus-far'
FOCUS_NEAR = 'focus-near'
FOCUS_STOP = 'focus-stop'

AUTO_WB = 'auto-wb'
WB_BLUE_PLUS = 'wb-blue-plus'
WB_BLUE_MINUS = 'wb-blue-minus'
WB_RED_PLUS = 'wb-red-plus'
WB_RED_MINUS = 'wb-red-minus'

PAN_LEFT = 'pan-left'
PAN_RIGHT = 'pan-right'

TILT_UP = 'tilt-up'
TILT_DOWN = 'tilt-down'

ZOOM_IN = 'zoom-in'
ZOOM_OUT = 'zoom-out'
ZOOM_STOP = 'zoom-stop'

TILT_INVERT_ON = 'tilt-invert-on'
TILT_INVERT_OFF = 'tilt-invert-off'
TILT_INVERT_TOGGLE = 'tilt-invert-toggle'

PAN_INVERT_ON = 'pan-invert-on'
PAN_INVERT_OFF = 'pan-invert-off'
PAN_INVERT_TOGGLE = 'pan-invert-toggle'

ZOOM_INVERT_ON = 'zoom-invert-on'
ZOOM_INVERT_OFF = 'zoom-invert-off'
ZOOM_INVERT_TOGGLE = 'zoom-invert-toggle'

ZOOM_AXIS_ON = 'zoom-axis-on'
ZOOM_AXIS_OFF = 'zoom-axis-off'
ZOOM_AXIS_TOGGLE = 'zoom-axis-toggle'

# Axes
PAN_AXIS = 'pan-axis'
TILT_AXIS = 'tilt-axis'
ZOOM_AXIS = 'zoom-axis'
SENSITIVITY_AXIS = 'sensitivity-axis'

# Parameres
KILL = 'kill'

PAN_AXIS_MULTIPLIER = 'pan-axis-multiplier'
TILT_AXIS_MULTIPLIER = 'tilt-axis-multiplier'
ZOOM_AXIS_MULTIPLIER = 'zoom-axis-multiplier'

ZOOM_AXIS_ENABLED = 'zoom-axis-enabled'
INVERT_PAN_AXIS = 'invert-pan-axis'
INVERT_TILT_AXIS = 'invert-tilt-axis'
INVERT_SENSITIVITY_AXIS = 'invert-sensitivity-axis'
INVERT_ZOOM_AXIS = 'invert-zoom-axis'
PAN_AXIS_DEAD_ZONE = 'pan-axis-dead-zone'
TILT_AXIS_DEAD_ZONE = 'tilt-axis-dead-zone'
ZOOM_AXIS_DEAD_ZONE = 'zoom-axis-dead-zone'
SENSITIVITY_AXIS_DEAD_ZONE = 'sensitivity-axis-dead-zone'

# Limits for visca commands
MAX_PAN_VALUE = 24
MIN_PAN_VALUE = -24
MAX_TILT_VALUE = 18
MIN_TILT_VALUE = -18
MAX_ZOOM_VALUE = 7
MIN_ZOOM_VALUE = -7


class JoystickState(object):
    def __init__(
            self,
            axes_value,
            hats_value,
            buttons_value,
    ):
        object.__init__(self)

        self.axes_value = axes_value
        self.hats_value = hats_value
        self.buttons_value = buttons_value

    def __eq__(self, other):
        if other is None:
            return False

        return all((
            self.axes_value == other.axes_value,
            self.hats_value == other.hats_value,
            self.buttons_value == other.buttons_value,
        ))

    def __ne__(self, other):
        return not (self == other)


class Foo(object):
    def __init__(self):
        object.__init__(self)

        self.joysticks = []
        self.joystick_states = []
        self.joystick_configs = []
        self.keyboard_config = {}

        self.current_joystick_states = None
        self.pressed_keys = None
        self.joystick_thread = None
        self.keep_running = False

        self.param_pan_axis_multiplier = []
        self.param_tilt_axis_multiplier = []
        self.param_zoom_axis_multiplier = []
        self.param_zoom_axis_enabled = []
        self.param_invert_pan_axis = []
        self.param_invert_tilt_axis = []
        self.param_invert_zoom_axis = []
        self.param_invert_sensitivity_axis = []
        self.param_pan_axis_dead_zone = []
        self.param_tilt_axis_dead_zone = []
        self.param_zoom_axis_dead_zone = []
        self.param_sensitivity_axis_dead_zone = []

        self.prev_zoom = 1
        self.zoom_mode = "stop"
        self.wb_mode = "auto"
        self.focus_mode = "auto"
        self.focus_action = "stop"

        self.zoom_active = False
        self.focus_active = False

        self.state_read_lock = threading.Condition()

        self.event_handlers = {
            pygame.QUIT: self._on_quit,
            pygame.JOYAXISMOTION: self._on_joy_axis_motion,
            pygame.JOYBUTTONDOWN: self._on_joy_button_down,
            pygame.JOYBUTTONUP: self._on_joy_button_up,
            pygame.JOYHATMOTION: self._on_joy_hat_motion,
        }

        self.command_handlers = {
            MEMORY_SET: self._memory,
            MEMORY_RECALL: self._memory,
            AUTO_FOCUS: self._focus,
            FOCUS_FAR: self._focus,
            FOCUS_NEAR: self._focus,
            FOCUS_STOP: self._focus,
            AUTO_WB: self._wb,
            WB_BLUE_PLUS: self._wb,
            WB_BLUE_MINUS: self._wb,
            WB_RED_PLUS: self._wb,
            WB_RED_MINUS: self._wb,
            ZOOM_IN: self._zoom,
            ZOOM_OUT: self._zoom,
            ZOOM_STOP: self._zoom,
            TILT_INVERT_ON: self._set_tilt_invert,
            TILT_INVERT_OFF: self._set_tilt_invert,
            TILT_INVERT_TOGGLE: self._set_tilt_invert,
            PAN_INVERT_ON: self._set_pan_invert,
            PAN_INVERT_OFF: self._set_pan_invert,
            PAN_INVERT_TOGGLE: self._set_pan_invert,
            ZOOM_INVERT_ON: self._set_zoom_invert,
            ZOOM_INVERT_OFF: self._set_zoom_invert,
            ZOOM_INVERT_TOGGLE: self._set_zoom_invert,
            ZOOM_AXIS_ON: self._set_zoom_axis,
            ZOOM_AXIS_OFF: self._set_zoom_axis,
            ZOOM_AXIS_TOGGLE: self._set_zoom_axis,
        }

        self.param_getters = {
            ZOOM_IN: self._get_zoom_in_param,
            ZOOM_OUT: self._get_zoom_out_param
        }

    def joystick_thread_runner(self):
        while self.keep_running:
            try:
                event = pygame.event.wait()
                self.proc_event(event)
            except RuntimeError:
                pass

    def proc_event(self, event):
        with self.state_read_lock:
            handler = self.event_handlers.get(event.type)
            if not handler:
                # print('Unknown event {}'.format(event.type))
                return

            handler(event)

        # Very crude but somewhat working solution to kill the program
        # if serial communication hangs for some reason
        kill_buttons = self.joystick_configs[0][CONFIG_PARAMETERS].get(KILL, None)
        if kill_buttons is not None:
            all_pressed = True
            for button in kill_buttons:
                if self.joystick_states[0].buttons_value[button] == 0:
                    all_pressed = False
            if all_pressed:
                print('Ending program')
                pygame.quit()
                os.kill(os.getpid(), signal.SIGKILL)

    def _on_quit(self, event):
        self.keep_running = False
        print("Received event 'Quit', exiting.")
        pygame.quit()
        exit(0)

    def _on_sigint(self, signal, frame):
        self.keep_running = False
        print("Received event 'CTRL-C', exiting.")
        pygame.quit()
        exit(0)

    def _on_joy_axis_motion(self, event):
        self.joystick_states[event.joy].axes_value[event.axis] = event.value

    def _on_joy_button_down(self, event):
        self.joystick_states[event.joy].buttons_value[event.button] = 1

    def _on_joy_button_up(self, event):
        self.joystick_states[event.joy].buttons_value[event.button] = 0

    def _on_joy_hat_motion(self, event):
        self.joystick_states[event.joy].hats_value[event.hat] = event.value

    def main(self):
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        #pygame.display.set_mode((100, 100), pygame.RESIZABLE)
        pysca.connect('/dev/ttyUSB0')
        pysca.set_power_on(1, True)
        pysca.set_wb_mode(1, "auto", blocking=True)
        pysca.set_focus_mode(1, "auto", blocking=True)
        signal.signal(signal.SIGINT, self._on_sigint)

        for i in range(0, pygame.joystick.get_count()):
            joystick = pygame.joystick.Joystick(i)
            joystick.init()

            num_axes = joystick.get_numaxes()
            num_hats = joystick.get_numhats()
            num_buttons = joystick.get_numbuttons()
            joystick_state = JoystickState(
                axes_value=[0.0] * num_axes,
                hats_value=[(0, 0)] * num_hats,
                buttons_value=[0] * num_buttons,
            )

            config_file_name = "configs/" + joystick.get_name() + ".json"
            # print("Opening joystick config: {}".format(config_file_name))
            with open(config_file_name, 'rt') as f:
                config = json.load(f)

            self.joystick_configs.append(config)
            self.joysticks.append(joystick)
            self.joystick_states.append(joystick_state)

        if not self.joystick_configs:
            config_file_name = "configs/" + "no_joystick" + ".json"
            with open(config_file_name, 'rt') as f:
                config = json.load(f)
            self.joystick_configs.append(config)
            joystick_state = JoystickState(
                axes_value=[0.0] * 1,
                hats_value=[(0, 0)] * 1,
                buttons_value=[0] * 1,
            )
            self.joystick_states.append(joystick_state)
            # print("Joystick not connected")

        config_file_name = "configs/" + "keyboard" + ".json"
        # print("Opening keyboard config: {}".format(config_file_name))
        with open(config_file_name, 'rt') as f:
            config = json.load(f)
        self.keyboard_config = config

        self.keep_running = True
        joystick_thread = threading.Thread(target=self.joystick_thread_runner, name="joystick-reader-thread")
        joystick_thread.start()

        try:
            self._main_loop()

        except KeyboardInterrupt:
            print("\n" "Interrupted")

        finally:
            if self.keep_running:
                self.keep_running = False

            joystick_thread.join(5)

    def get_joystick_layout(self, joystick_index):
        i = 1
        while True:
            layout_str_key = LAYOUT + str(i)
            if layout_str_key in self.joystick_configs[joystick_index]:
                layout_button = self.joystick_configs[joystick_index][layout_str_key][LAYOUT_BUTTON]
                if self.joystick_states[joystick_index].buttons_value[layout_button] == 1:
                    return self.joystick_configs[joystick_index][layout_str_key]
            else:
                break
            i += 1
        return self.joystick_configs[joystick_index][DEFAULT_LAYOUT]

    def get_keyboard_layout(self):
        i = 1
        while True:
            layout_str_key = LAYOUT + str(i)
            if layout_str_key in self.keyboard_config:
                layout_key = self.keyboard_config[layout_str_key][LAYOUT_KEY]
                key = getattr(pygame, layout_key)
                if key in self.pressed_keys:
                    return self.keyboard_config[layout_str_key]
            else:
                break
            i += 1
        return self.keyboard_config[DEFAULT_LAYOUT]

    def get_pressed_keys(self):
        pressed_keys = set()
        for i, value in enumerate(pygame.key.get_pressed()):
            if value == 1:
                pressed_keys.add(i)
        return pressed_keys

    def get_pressed_buttons(self, joystick_index):
        pressed_buttons = set()
        for i, value in enumerate(self.current_joystick_states[joystick_index].buttons_value):
            if value == 1:
                pressed_buttons.add(i)
        return pressed_buttons

    def get_active_hats(self, joystick_index):
        active_hats = []
        hats_states = self.current_joystick_states[joystick_index].hats_value
        for i, hat in enumerate(hats_states):
            if hat[0] == 1:
                active_hats.append([i, "right"])
            if hat[0] == -1:
                active_hats.append([i, "left"])
            if hat[1] == 1:
                active_hats.append([i, "up"])
            if hat[1] == -1:
                active_hats.append([i, "down"])
        return active_hats

    def merge_two_dicts(self, d1, d2):
        merged = d1.copy()
        merged.update(d2)
        return merged

    def get_params(self, dict, action, joystick_index=None):
        params = {}

        if joystick_index is not None:
            params["joystick_index"] = joystick_index

        param_getter = self.param_getters.get(action, None)
        if param_getter is not None:
            param = param_getter(joystick_index)
            params = self.merge_two_dicts(params, param)

        param = dict.get("params", None)
        if param is not None:
            params = self.merge_two_dicts(params, param)

        return params

    def find_actions_for_buttons(self, buttons, joystick_index, actions):
        layout = self.get_joystick_layout(joystick_index)
        layout_buttons = layout[CONFIG_BUTTONS]

        for key, value in layout_buttons.iteritems():
            if isinstance(value, list):
                # List of dicts where "button" stores button id and "param" parameter for command
                for d in value:
                    if d["button"] in buttons:
                        actions[key] = self.get_params(d, key, joystick_index)
            elif isinstance(value, dict):
                # Dict where "button" stores button id and "param" parameter for command
                if value["button"] in buttons:
                    actions[key] = self.get_params(value, key, joystick_index)
            else:
                # Just the id for the button
                if value in buttons:
                    actions[key] = self.get_params({}, key, joystick_index)

        return actions

    def find_actions_for_hats(self, hats, joystick_index, actions):
        layout = self.get_joystick_layout(joystick_index)
        layout_hats = layout[CONFIG_HATS]

        for key, value in layout_hats.iteritems():
            if isinstance(value, list):
                # List of dicts where "id" stores hat id, "dir" hat direction and "param" parameter for command
                for d in value:
                    if [d["id"], d["dir"]] in hats:
                        actions[key] = self.get_params(d, key, joystick_index)
            else:
                # Dict where "id" stores hat id, "dir" hat direction and "param" parameter for command
                if [value["id"], value["dir"]] in hats:
                    actions[key] = self.get_params(value, key, joystick_index)

        return actions

    def find_actions_for_keys(self, keys, actions):
        layout = self.get_keyboard_layout()
        layout_keys = layout[CONFIG_KEYS]

        for key, value in layout_keys.iteritems():
            if isinstance(value, list):
                # List of dicts where "key" stores key id and "param" parameter for command
                for d in value:
                    if getattr(pygame, d["key"]) in keys:
                        actions[key] = self.get_params(d, key)
            elif isinstance(value, dict):
                # Dict where "key" stores key id and "param" parameter for command
                if getattr(pygame, value["key"]) in keys:
                    actions[key] = self.get_params(value, key)
            else:
                # Just the id for the key
                if getattr(pygame, value) in keys:
                    actions[key] = self.get_params({}, key)

        return actions

    def get_actions(self):
        actions = {}

        for joystick_index in range(0,len(self.joystick_configs)):
            self.find_actions_for_hats(self.get_active_hats(joystick_index), joystick_index, actions)
            self.find_actions_for_buttons(self.get_pressed_buttons(joystick_index), joystick_index, actions)

        self.find_actions_for_keys(self.pressed_keys, actions)

        return actions

    def handle_zoom_and_focus(self, zoom, actions):
        if zoom > 0:
            actions[ZOOM_IN] = {"speed": zoom}
        elif zoom < 0:
            actions[ZOOM_OUT] = {"speed": zoom}

        if ZOOM_IN not in actions and ZOOM_OUT not in actions:
            if self.zoom_active is True:
                actions[ZOOM_STOP] = {}
                self.zoom_active = False
        else:
            self.zoom_active = True

        if FOCUS_FAR not in actions and FOCUS_NEAR not in actions and AUTO_FOCUS not in actions:
            if self.focus_active is True:
                actions[FOCUS_STOP] = {}
                self.focus_active = False
        else:
            self.focus_active = True

        return actions

    def handle_pan_and_tilt(self, pan, tilt, actions):
        if PAN_LEFT in actions:
            pan = -1*actions[PAN_LEFT]["speed"]
            del actions[PAN_LEFT]

        if PAN_RIGHT in actions:
            pan = actions[PAN_RIGHT]["speed"]
            del actions[PAN_RIGHT]

        if TILT_UP in actions:
            tilt = -1*actions[TILT_UP]["speed"]
            del actions[TILT_UP]

        if TILT_DOWN in actions:
            tilt = actions[TILT_DOWN]["speed"]
            del actions[TILT_DOWN]

        return (pan, tilt, actions)

    def initialize_joystick_parameters(self):
        for i, joystick_config in enumerate(self.joystick_configs):
            self.param_pan_axis_multiplier.append(joystick_config[CONFIG_PARAMETERS].get(PAN_AXIS_MULTIPLIER, False))
            self.param_tilt_axis_multiplier.append(joystick_config[CONFIG_PARAMETERS].get(TILT_AXIS_MULTIPLIER, False))
            self.param_zoom_axis_multiplier.append(joystick_config[CONFIG_PARAMETERS].get(ZOOM_AXIS_MULTIPLIER, 1))
            self.param_zoom_axis_enabled.append(joystick_config[CONFIG_PARAMETERS].get(ZOOM_AXIS_ENABLED, True))
            self.param_invert_pan_axis.append(joystick_config[CONFIG_PARAMETERS].get(INVERT_PAN_AXIS, False))
            self.param_invert_tilt_axis.append(joystick_config[CONFIG_PARAMETERS].get(INVERT_TILT_AXIS, False))
            self.param_invert_zoom_axis.append(joystick_config[CONFIG_PARAMETERS].get(INVERT_ZOOM_AXIS, False))
            self.param_invert_sensitivity_axis.append(joystick_config[CONFIG_PARAMETERS].get(INVERT_SENSITIVITY_AXIS, False))
            self.param_pan_axis_dead_zone.append(joystick_config[CONFIG_PARAMETERS].get(PAN_AXIS_DEAD_ZONE, 0.1))
            self.param_tilt_axis_dead_zone.append(joystick_config[CONFIG_PARAMETERS].get(TILT_AXIS_DEAD_ZONE, 0.1))
            self.param_zoom_axis_dead_zone.append(joystick_config[CONFIG_PARAMETERS].get(ZOOM_AXIS_DEAD_ZONE, 0.1))
            self.param_sensitivity_axis_dead_zone.append(joystick_config[CONFIG_PARAMETERS].get(SENSITIVITY_AXIS_DEAD_ZONE, 0.1))

    def get_sensitivity(self, joystick_index):
        sensitivity_axis = self.joystick_configs[joystick_index][CONFIG_AXES].get(SENSITIVITY_AXIS, None)
        sensitivity_axis_value = 1.0
        if sensitivity_axis is not None:
            sensitivity_axis_value = self.current_joystick_states[joystick_index].axes_value[sensitivity_axis]
            if abs(sensitivity_axis_value) <= self.param_sensitivity_axis_dead_zone[joystick_index]:
                sensitivity_axis_value = 0.0
            sensitivity_axis_value = (sensitivity_axis_value * -1) + 1.0
            if self.param_invert_sensitivity_axis[joystick_index]:
                sensitivity_axis_value = -1 * (sensitivity_axis_value - 2.0)
        return sensitivity_axis_value

    def get_pan(self, joystick_index, sensitivity_multiplier):
        pan_axis = self.joystick_configs[joystick_index][CONFIG_AXES].get(PAN_AXIS, None)
        pan_axis_value = 0.0

        if pan_axis is not None:
            pan_axis_value = self.current_joystick_states[joystick_index].axes_value[pan_axis]

        if abs(pan_axis_value) <= self.param_pan_axis_dead_zone[joystick_index]:
            pan_axis_value = 0.0

        pan_axis_multiplier = 1 + sensitivity_multiplier * self.param_pan_axis_multiplier[joystick_index]
        pan_invert_value = -1 if self.param_invert_pan_axis[joystick_index] else 1
        pan = pan_invert_value * clip(int(pan_axis_multiplier * pan_axis_value), MIN_PAN_VALUE, MAX_PAN_VALUE)
        
        return pan
    
    def get_tilt(self, joystick_index, sensitivity_multiplier):
        tilt_axis = self.joystick_configs[joystick_index][CONFIG_AXES].get(TILT_AXIS, None)
        tilt_axis_value = 0.0

        if tilt_axis is not None:
            tilt_axis_value = self.current_joystick_states[joystick_index].axes_value[tilt_axis]

        if abs(tilt_axis_value) <= self.param_tilt_axis_dead_zone[joystick_index]:
            tilt_axis_value = 0.0

        tilt_axis_multiplier = 1 + sensitivity_multiplier * self.param_tilt_axis_multiplier[joystick_index]
        tilt_invert_value = 1 if self.param_invert_tilt_axis[joystick_index] else -1
        tilt = tilt_invert_value * clip(int(tilt_axis_multiplier * tilt_axis_value), MIN_TILT_VALUE, MAX_TILT_VALUE)

        return tilt

    def get_zoom(self, joystick_index, sensitivity_multiplier):
        zoom_axis = self.joystick_configs[joystick_index][CONFIG_AXES].get(ZOOM_AXIS, None)
        zoom_axis_value = 0.0

        if zoom_axis is not None:
            zoom_axis_value = self.current_joystick_states[joystick_index].axes_value[zoom_axis]

        if abs(zoom_axis_value) <= self.param_zoom_axis_dead_zone[joystick_index]:
            zoom_axis_value = 0.0

        zoom_axis_multiplier = sensitivity_multiplier * self.param_zoom_axis_multiplier[joystick_index]
        zoom = 0
        if self.param_zoom_axis_enabled[joystick_index] and zoom_axis_value != 0.0:
            if zoom_axis_value < 0:
                zoom_value = zoom_axis_value - 1.0
            else:
                zoom_value = zoom_axis_value + 1.0
            zoom = clip(int(zoom_value + (zoom_axis_multiplier * zoom_axis_value)), MIN_ZOOM_VALUE-1, MAX_ZOOM_VALUE+1)
            zoom = zoom if not self.param_invert_zoom_axis[joystick_index] else -1 * zoom

        return zoom

    def _get_zoom_in_param(self, joystick_index):
        param = {}
        if joystick_index is not None:
            sensitivity_axis_value = self.get_sensitivity(joystick_index)
            zoom = clip(int(sensitivity_axis_value * 3.5), 0, MAX_ZOOM_VALUE + 1)
            param["speed"] = zoom
        return param

    def _get_zoom_out_param(self, joystick_index):
        param = {}
        if joystick_index is not None:
            sensitivity_axis_value = self.get_sensitivity(joystick_index)
            zoom = clip(int(sensitivity_axis_value * 3.5), 0, MAX_ZOOM_VALUE + 1)
            param["speed"] = -1 * zoom
        return param

    def get_ptz_from_axes(self):
        pan = 0
        tilt = 0
        zoom = 0
        for i, joystick_config in enumerate(self.joystick_configs):
            sensitivity_axis_value = self.get_sensitivity(i)
            if pan == 0:
                pan = self.get_pan(i, sensitivity_axis_value)
            if tilt == 0:
                tilt = self.get_tilt(i, sensitivity_axis_value)
            if zoom == 0:
                zoom = self.get_zoom(i, sensitivity_axis_value)
        return (pan, tilt, zoom)

    def _memory(self, cmd, mem=0, joystick_index=None):
        if cmd == MEMORY_SET:
            pysca.set_memory(1, mem, blocking=True)
        elif cmd == MEMORY_RECALL:
            pysca.recall_memory(1, mem, blocking=True)

    def _focus(self, cmd, joystick_index=None):
        if cmd == AUTO_FOCUS:
            if self.focus_mode != "auto":
                pysca.set_focus_mode(1, "auto", blocking=True)
                self.focus_mode = "auto"
            pysca.set_focus_mode(1, "trigger", blocking=True)

        if cmd in {FOCUS_FAR, FOCUS_NEAR}:
            if self.focus_mode != "manual":
                pysca.set_focus_mode(1, "manual", blocking=True)
                self.focus_mode = "manual"
            if cmd == FOCUS_FAR:
                if self.focus_action != "far":
                    pysca.focus(1, "far", speed=2, blocking=True)
                    self.focus_action = "far"
            elif cmd == FOCUS_NEAR:
                if self.focus_action != "near":
                    pysca.focus(1, "near", speed=2, blocking=True)
                    self.focus_action = "near"

        if cmd == FOCUS_STOP and self.focus_action != "stop":
            pysca.focus(1, "stop", blocking=True)
            self.focus_action = "stop"

    def _wb(self, cmd, joystick_index=None):
        if cmd == AUTO_WB:
            if self.wb_mode != "auto":
                pysca.set_wb_mode(1, "auto", blocking=True)
                self.wb_mode = "auto"

        if cmd in {WB_RED_PLUS, WB_RED_MINUS, WB_BLUE_PLUS, WB_BLUE_MINUS}:
            if self.wb_mode != "manual":
                pysca.set_wb_mode(1, "manual", blocking=True)
                self.wb_mode = "manual"
            if cmd == WB_RED_PLUS:
                pysca.set_red_gain(1, "up", blocking=True)
            elif cmd == WB_RED_MINUS:
                pysca.set_red_gain(1, "down", blocking=True)
            elif cmd == WB_BLUE_PLUS:
                pysca.set_blue_gain(1, "up", blocking=True)
            elif cmd == WB_BLUE_MINUS:
                pysca.set_blue_gain(1, "down", blocking=True)

    def _zoom(self, cmd, speed=0, joystick_index=None):
        if cmd == ZOOM_OUT and (self.zoom_mode != "wide" or self.prev_zoom != speed):
            pysca.zoom(1, "wide", speed=-1*speed, blocking=True)
            self.zoom_mode = "wide"
            self.prev_zoom = speed
        elif cmd == ZOOM_IN and (self.zoom_mode != "tele" or self.prev_zoom != speed):
            pysca.zoom(1, "tele", speed=speed, blocking=True)
            self.zoom_mode = "tele"
            self.prev_zoom = speed
        elif (cmd == ZOOM_STOP) and self.zoom_mode != "stop":
            pysca.zoom(1, "stop", blocking=True)
            self.zoom_mode = "stop"
            self.prev_zoom = speed

    def _set_tilt_invert(self, cmd, joystick_index=0):
        if cmd == TILT_INVERT_ON:
            self.param_invert_tilt_axis[joystick_index] = True
        if cmd == TILT_INVERT_OFF:
            self.param_invert_tilt_axis[joystick_index] = False
        if cmd == TILT_INVERT_TOGGLE:
            self.param_invert_tilt_axis[joystick_index] = not self.param_invert_tilt_axis[joystick_index]

    def _set_pan_invert(self, cmd, joystick_index=0):
        if cmd == PAN_INVERT_ON:
            self.param_invert_pan_axis[joystick_index] = True
        if cmd == PAN_INVERT_OFF:
            self.param_invert_pan_axis[joystick_index] = False
        if cmd == PAN_INVERT_TOGGLE:
            self.param_invert_pan_axis[joystick_index] = not self.param_invert_pan_axis[joystick_index]

    def _set_zoom_invert(self, cmd, joystick_index=0):
        if cmd == PAN_INVERT_ON:
            self.param_invert_zoom_axis[joystick_index] = True
        if cmd == PAN_INVERT_OFF:
            self.param_invert_zoom_axis[joystick_index] = False
        if cmd == PAN_INVERT_TOGGLE:
            self.param_invert_zoom_axis[joystick_index] = not self.param_invert_pan_axis[joystick_index]

    def _set_zoom_axis(self, cmd, joystick_index=0):
        if cmd == ZOOM_AXIS_ON:
            self.param_zoom_axis_enabled[joystick_index] = True
        if cmd == ZOOM_AXIS_OFF:
            self.param_zoom_axis_enabled[joystick_index] = False
        if cmd == ZOOM_AXIS_TOGGLE:
            self.param_zoom_axis_enabled[joystick_index] = not self.param_zoom_axis_enabled[joystick_index]

    def _main_loop(self):
        clock = pygame.time.Clock()
        prev_joystick_states = None
        prev_pressed_keys = None

        self.initialize_joystick_parameters()

        while self.keep_running:
            clock.tick(10)

            with self.state_read_lock:
                # self.joystick_states is updated by joystick_thread
                self.current_joystick_states = copy.deepcopy(self.joystick_states)

            self.pressed_keys = self.get_pressed_keys()

            # TODO not interested in pressed keys, but in found actions
            if prev_joystick_states == self.current_joystick_states and prev_pressed_keys == self.pressed_keys:
                continue

            prev_joystick_states = copy.deepcopy(self.current_joystick_states)
            prev_pressed_keys = copy.deepcopy(self.pressed_keys)

            ptz = self.get_ptz_from_axes()
            pan = ptz[0]
            tilt = ptz[1]
            zoom = ptz[2]

            actions = self.get_actions()
            actions = self.handle_zoom_and_focus(zoom, actions)
            modified = self.handle_pan_and_tilt(pan, tilt, actions)
            pan = modified[0]
            tilt = modified[1]
            actions = modified[2]

            # print("Actions: {}".format(actions))
            # print("Pan: {}, tilt: {}".format(pan, tilt))

            pysca.pan_tilt(1, pan=pan, tilt=tilt, blocking=True)

            for action, params in actions.iteritems():
                handler = self.command_handlers.get(action)
                handler(action, **params)


if __name__ == "__main__":
    foo = Foo()
    foo.main()
