#!/usr/bin/env python
"""Load Demos"""

import os
import importlib

DEMO_IAAS = ['OpenStack']

if __name__ == "__main__":
    INF = os.environ.get('DEMO_IAAS', None)
    if INF:
        DEMO = importlib.import_module("demo_env_%s" % INF.lower())
        DEMO.demo()
    else:
        print("\nAvailable Infrastructure Demos:\n")
        for indx, env in enumerate(DEMO_IAAS):
            print("\t%d) %s" % ((indx + 1), env))
        print("\n")

        IMPORTED_DEMO = False
        while not IMPORTED_DEMO:
            ENV_INDX = input('Which demo do you want: ')
            try:
                if len(DEMO_IAAS) >= int(ENV_INDX):
                    ENV = DEMO_IAAS[int(ENV_INDX) - 1]
                    DEMO = importlib.import_module("demo_env_%s" % ENV.lower())
                    IMPORTED_DEMO = True
                    DEMO.populate()
            except ImportError:
                pass
