#!/usr/bin/python3

from __future__ import print_function
import argparse

parser = argparse.ArgumentParser()


def crash_or_not(crash_commanded):
    some_value = 1
    if crash_commanded:
        some_value -= 1
    print("All good, you get {}".format(1 / some_value))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--crash", help="Do something that causes a crash", action="store_true")
    args = parser.parse_args()
    crash_or_not(args.crash)


# If the traceplus module is found use it, otherwise run main() directly.
if __name__ == '__main__':
    try:
        import traceplus
    except ImportError:
        main()
    else:
        traceplus.RunWithExpandedTrace(main)
