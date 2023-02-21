import yaml
import logging
import requests
import os


def load_yaml(args):
    with open(args.yaml, "r") as stream:
        return (yaml.safe_load(stream))


def create_user_config(yaml):
    logging.info("creating include file")
    sources = get_project_source(yaml)
    top_module = get_top_module(yaml)

    if top_module == 'top':
        logging.error("top module cannot be called top - prepend your repo name to make it unique")
        exit(1)

    filename = 'user_config.tcl'
    with open(os.path.join('src', filename), 'w') as fh:
        fh.write("set ::env(DESIGN_NAME) {}\n".format(top_module))
        fh.write('set ::env(VERILOG_FILES) "\\\n')
        for line, source in enumerate(sources):
            fh.write("    $::env(DESIGN_DIR)/" + source)
            if line != len(sources) - 1:
                fh.write(' \\\n')
        fh.write('"\n')


def fetch_file(url, filename):
    logging.info("trying to download {}".format(url))
    r = requests.get(url)
    if r.status_code != 200:
        logging.warning("couldn't download {}".format(url))
        exit(1)

    with open(filename, 'wb') as fh:
        logging.info("written to {}".format(filename))
        fh.write(r.content)


def get_project_source(yaml):
    # wokwi_id must be an int or 0
    try:
        wokwi_id = int(yaml['project']['wokwi_id'])
    except ValueError:
        logging.error("wokwi id must be an integer")
        exit(1)

    # it's a wokwi project
    if wokwi_id != 0:
        url = "https://wokwi.com/api/projects/{}/verilog".format(wokwi_id)
        src_file = "user_module_{}.v".format(wokwi_id)
        fetch_file(url, os.path.join("src", src_file))

        # also fetch the wokwi diagram
        url = "https://wokwi.com/api/projects/{}/diagram.json".format(wokwi_id)
        diagram_file = "wokwi_diagram.json"
        fetch_file(url, os.path.join("src", diagram_file))

        return [src_file, 'cells.v']

    # else it's HDL, so check source files
    else:
        if 'source_files' not in yaml['project']:
            logging.error("source files must be provided if wokwi_id is set to 0")
            exit(1)

        source_files = yaml['project']['source_files']
        if source_files is None:
            logging.error("must be more than 1 source file")
            exit(1)

        if len(source_files) == 0:
            logging.error("must be more than 1 source file")
            exit(1)

        if 'top_module' not in yaml['project']:
            logging.error("must provide a top module name")
            exit(1)

        for filename in source_files:
            if not os.path.exists(os.path.join('src', filename)):
                logging.error(f"{filename} doesn't exist in the repo")
                exit(1)

        return source_files


def get_top_module(yaml):
    wokwi_id = int(yaml['project']['wokwi_id'])
    if wokwi_id != 0:
        return "user_module_{}".format(wokwi_id)
    else:
        return yaml['project']['top_module']
