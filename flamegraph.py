#!/bin/python
from string import Formatter
import yaml


def transform(cmd):
    a = cmd["status"].split(' - ')
    if len(a) != 3:
        return ()
    return (cmd["runtime_s"], a[2], a[1])


def make_branched(ops):
    jobs = list(filter(None, map(transform, ops)))
    roots = []
    plot_list = []
    task_list = []
    for time, root, task in jobs:
        if not roots:
            roots.append(root)
            plot_list.append([time])
            task_list.append([task])
        elif roots[-1] == root:
            plot_list[-1].append(time)
            task_list[-1].append(task)
        else:
            roots.append(root)
            plot_list.append([time])
            task_list.append([task])
    return roots, plot_list, task_list


def strfdelta(tdelta, fmt):
    f = Formatter()
    d = {}
    li = {'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
    k = list(map(lambda x: x[1], list(f.parse(fmt))))
    rem = int(tdelta)

    for i in ('D', 'H', 'M', 'S'):
        if i in k and i in li.keys():
            d[i], rem = divmod(rem, li[i])

    return f.format(fmt, **d)


def read_ops(filename):
    with open(filename, 'r') as f:
        y = f.read()
    return yaml.safe_load_all(y)


def format_ops(ops, threshold):
    output = ""
    plot_list = make_branched(ops)
    for root, times, tasks in zip(*plot_list):
        header_printed = False
        for time, task in zip(times, tasks):
            if time >= threshold:
                if not header_printed:
                    output += f"{root}:\n"
                    header_printed = True
                delta_str = strfdelta(time, '{H:02}h {M:02}m {S:02}s')
                output += f"\t{task}: {delta_str}\n"
    return output


def flamegraph(ops):
    output = ""
    plot_list = make_branched(ops)
    for root, times, tasks in zip(*plot_list[:3]):
        output += f"{root} 0\n"
        for time, task in zip(times, tasks):
            output += f"{root};{task} {time}\n"
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="OpenLane cmds.log file")
    parser.add_argument("--ignore-sec", type=int, default=0,
                        help="""Minimum runtime of commands to leave out from\
                            the output in seconds. Ignored when --flamegraph \
                                is used""")
    parser.add_argument("--flamegraph",
                        help="""Print flamegraph inputs instead of human \
                            readable""",
                        action="store_true")
    args = parser.parse_args()

    ops = read_ops(args.filename)
    if not args.flamegraph:
        print(format_ops(next(ops), args.ignore_sec))
    else:
        print(flamegraph(next(ops)), end="")
