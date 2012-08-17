#!/usr/bin/env python
import argparse
import sys

def main(raw_arguments):
    parser = argparse.ArgumentParser(description='Simple oh-bugimporters crawl program')

    parser.add_argument('-i', action="store", dest="input")
    parser.add_argument('-o', action="store", dest="output")

    args = parser.parse_args(raw_arguments)
    print args

if __name__ == '__main__':
    main(sys.argv[1:])
