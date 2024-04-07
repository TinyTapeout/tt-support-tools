# Usage:
# klayout -b -r gds_compare.py -rd gds1=file1.gds -rd gds2=file2.gds

import sys

import pya


def compare_gds(file1, file2):
    diff = pya.LayoutDiff()

    # Load the layouts
    layout1 = pya.Layout()
    layout1.read(file1)

    layout2 = pya.Layout()
    layout2.read(file2)

    # Check if the layouts are identical
    return diff.compare(layout1, layout2)


def main():
    if compare_gds(gds1, gds2):  # noqa: F821
        sys.exit(0)
    else:
        sys.exit(-1)

if __name__ == "__main__":
    main()
