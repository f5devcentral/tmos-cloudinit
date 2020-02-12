import os
import sys


def clear_screen():
    if sys.platform.startswith('win'):
        os.system('cls')
    else:
        os.system('clear')


def print_screen(header=None, message=None, prompt=None, menu=None, exit=False):
    clear_screen()
    print(header)
    if message:
        print(message)
        print('\n')
    if exit:
        sys.exit(1)
    if menu:
        for index, item in enumerate(menu['items']):
            print("\t%d) %s" % (index + 1, item))
        print('\n')
        menu_indx = input(menu['prompt'])
        if len(menu['items']) >= int(menu_indx):
            return (menu_indx-1)
    elif(prompt):
        return raw_input(prompt)
