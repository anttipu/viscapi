#!/usr/bin/env python2

from __future__ import division, absolute_import, unicode_literals, print_function

import threading
import pygame

config = {
    "buttons": {
        "auto-wb": 1,
        "auto-focus": 0,
    }
}

AUTO_FOCUS = 'auto-focus'
AUTO_WHITE_BALANCE = 'auto-wb'


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
        self.keep_running = True

        self.event_handlers = {
            pygame.QUIT: self._on_quit,
            pygame.JOYAXISMOTION: self._on_joy_axis_motion,
            pygame.JOYBUTTONDOWN: self._on_joy_button_down,
            pygame.JOYBUTTONUP: self._on_joy_button_up,
            pygame.JOYHATMOTION: self._on_joy_hat_motion,
            pygame.KEYDOWN: self._on_keyboard_button_down,
            pygame.KEYUP: self._on_keyboard_button_up
        }

    def joystick_thread_runner(self):
        while self.keep_running:
            event = pygame.event.wait()
            self.proc_event(event)

    def proc_event(self, event):
        handler = self.event_handlers.get(event.type)
        if not handler:
            print('Unknown event {}'.format(event.type))
            return

        handler(event)

    def _on_joy_axis_motion(self, event):
        self.joystick_states[event.joy].axes_value[event.axis] = event.value

    def _on_joy_button_down(self, event):
        self.joystick_states[event.joy].buttons_value[event.button] = 1

    def _on_joy_button_up(self, event):
        self.joystick_states[event.joy].buttons_value[event.button] = 0

    def _on_joy_hat_motion(self, event):
        self.joystick_states[event.joy].hats_value[event.hat] = event.value

    def _on_keyboard_button_down(self, event):
        print("Keyboard button down: {}".format(event))

    def _on_keyboard_button_up(self, event):
        print("Keyboard button up: {}".format(event))

    def _on_quit(self, event):
        self.keep_running = False
        print("Received event 'Quit', exiting. {}".format(event))
        exit(0)

    def main(self):
        # os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.display.set_mode((100, 100), pygame.RESIZABLE)
        pygame.init()

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

            self.joysticks.append(joystick)
            self.joystick_states.append(joystick_state)

        clock = pygame.time.Clock()
        joystick_thread = threading.Thread(target=self.joystick_thread_runner, name="joystick-reader-thread")
        joystick_thread.start()

        try:
            while self.keep_running:
                clock.tick(5)
                # event = pygame.event.wait()
                # self.proc_event(event)
                for i in range(0, pygame.joystick.get_count()):
                    print("Joystick {}:".format(self.joysticks[i].get_name()))
                    print(" axes: {}".format(self.joystick_states[i].axes_value))
                    print(" hats: {}".format(self.joystick_states[i].hats_value))
                    pressed_buttons = set()
                    for j, button in enumerate(self.joystick_states[i].buttons_value):
                        if button == 1:
                            pressed_buttons.add(j)
                    print(" buttons: {}, {}".format(self.joystick_states[i].buttons_value, pressed_buttons))

        except KeyboardInterrupt:
            print("\n" "Interrupted")

        finally:
            if self.keep_running:
                self.keep_running = False


if __name__ == "__main__":
    foo = Foo()
    foo.main()
