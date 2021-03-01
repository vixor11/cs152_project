#!/usr/bin/env python

import os
import sys

# file imports all the pip modules we need at once
def main(argv):
    os.system("pip install discord & pip install schedule & pip install better_profanity & pip install time")

if __name__ == "__main__":
    main(sys.argv[1:])