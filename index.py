#!/usr/bin/env python

import importlib.util
import argparse
import random
import mqtt
import time

from os import path
from time import sleep
from glob import glob


class LichtKrant:

    def __init__(self, args):
        self.args = args
        mqtt.connect(not args.offline)
        self.modules = self.read_modules(self.args.state_dir + '**/**/*.mod.py')

    def import_module(self, loc):
        name = path.basename(loc).replace('.mod.py', '', -1)
        spec = importlib.util.spec_from_file_location(name, loc)
        module = spec.loader.load_module()
        return module

    def read_modules(self, location):
        # loading state modules
        return [self.import_module(file) for file in glob(location, recursive=self.args.recursive)]

    def get_state(self, space_state):
        # States need to be re-created, since a thread can only be start()ed once
        states = [module.State() for module in self.modules]
        # getting highest indexed state
        if self.args.module is not None:
            try:
                return [s for s in states if s.name == args.module][0]
            except IndexError:
                raise Exception('The module passed does not exist.')

        # filter states
        filtered_states = [state for state in states if state.check(space_state)]

        # return random with highest index
        random.shuffle(filtered_states)

        if len(filtered_states) == 0:
            return None

        return sorted(filtered_states, key=lambda s: s.index, reverse=True)[0]

    def run_state(self, state):
        # running states
        if self.args.dry:
            print(f"state: {state.name}")
            return None

        state.start()
        return state

    def state_loop(self):
        # the state update loop
        current_state = None
        current_thread = None

        while True:
            space_state = mqtt.get_states()
            new_state = self.get_state(space_state)

            if new_state != current_state:
                current_state = new_state

                if current_thread is not None:
                    current_thread.kill()
                    current_thread.join()
                    sleep(1)  # sleep to reset outlining

                if current_state is not None:
                    current_thread = self.run_state(current_state)

            # delay or force update if necessary
            end_time = time.time() + new_state.delay

            while True:
                if time.time() >= end_time:
                    break

                diff_state = self.get_state(space_state)

                if diff_state.index > new_state.index:
                    break

                sleep(4)

    def start(self):
        try:
            self.state_loop()
        except KeyboardInterrupt:
            pass  # no ugly error message


if __name__ == '__main__':
    # parsing command-line arguments
    parser = argparse.ArgumentParser(description='A driver for the DJO Lichtkrant project.')

    parser.add_argument('-m', '--module', default=None, help='load a specific module by name')
    parser.add_argument('-s', '--state-dir', default='./states', help='path to the states directory')
    parser.add_argument('-r', '--recursive', type=bool, default=True, help='whether to search recursively')
    parser.add_argument('-d', '--dry', action='store_true', default=False, help='do not spew out pixel data')
    parser.add_argument('-o', '--offline', action='store_true', default=False, help='disable MQTT connectivity')

    args = parser.parse_args()

    lichtkrant = LichtKrant(args)
    lichtkrant.start()
