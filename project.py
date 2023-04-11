import yaml
import logging
import requests
import os
import subprocess
import shutil
import glob
import re


def load_yaml(args):
    with open(args.yaml, "r") as stream:
        return (yaml.safe_load(stream))


def print_wokwi_id(yaml):
    print(yaml['project']['wokwi_id'])


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
        return False

    with open(filename, 'wb') as fh:
        logging.info("written to {}".format(filename))
        fh.write(r.content)
        
    return True


def fetch_wokwi_file(wokwi_id:int, file_requested:str, 
                     destination_name:str = None):
    '''
        fetch_wokwi_file -- perform a request on the wokwi api to 
                            retrieve a file from a given project.
                            
        @param wokwi_id: project id (integer)
        @param file_requested: the specific file requested for the 
                project, e.g. verilog or diagram.json
        @param destination_name: file to write out to with result
    '''
    if destination_name is None or not len(destination_name):
        destination_name = file_requested
        
    url = f'https://wokwi.com/api/projects/{wokwi_id}/{file_requested}'
    return fetch_file(url, destination_name)


def install_wokwi_testing(wokwi_id:int, destination_dir:str='src', 
                          resource_dir:str=None):
    
    wokwi_id_str = str(wokwi_id)
    #wokwi_user_module = f'user_module_{wokwi_'
    
    if resource_dir is None or not len(resource_dir):
        resource_dir = os.path.join(os.path.dirname(__file__), 'testing')
        
        
    # directories in testing/lib to copy over
    pyLibsDir = os.path.join(resource_dir, 'lib')
    
    # src template dir
    srcTplDir = os.path.join(resource_dir, 'src-tpl')
    
    for libfullpath in glob.glob(os.path.join(pyLibsDir, '*')):
        logging.info(f'Copying {libfullpath} to {destination_dir}')
        shutil.copytree(
            libfullpath,
            os.path.join(destination_dir, os.path.basename(libfullpath)),
            dirs_exist_ok=True)
        
        
    
    
    for srcTemplate in glob.glob(os.path.join(srcTplDir, '*')):
        with open(srcTemplate, 'r') as f:
            contents = f.read()
            customizedContents = re.sub('WOKWI_ID', wokwi_id_str, contents)
            outputFname = os.path.basename(srcTemplate)
            with open(os.path.join(destination_dir, outputFname), 'w') as outf:
                logging.info(f'writing src tpl to {outputFname}')
                outf.write(customizedContents)
                outf.close()
    
    
            
            
        
    
        
def get_project_source(yaml):
    # wokwi_id must be an int or 0
    try:
        wokwi_id = int(yaml['project']['wokwi_id'])
    except ValueError:
        logging.error("wokwi id must be an integer")
        exit(1)

    # it's a wokwi project
    if wokwi_id != 0:
        src_file = f'user_module_{wokwi_id}.v'
        if not fetch_wokwi_file(wokwi_id, 'verilog', 
                         os.path.join("src", src_file) ):
            logging.error(f'Could not fetch verilog file for wokwi project {wokwi_id}')
            exit(1)
        

        # also fetch the wokwi diagram
        if not fetch_wokwi_file(wokwi_id, 'diagram.json', 
                            os.path.join("src", 'wokwi_diagram.json')):
            logging.error(f'Could not fetch diagram.json file for wokwi project {wokwi_id}')
            exit(1)
        
        
        # attempt to download the *optional* truthtable for the project
        if fetch_wokwi_file(wokwi_id, 'truthtable.md', 
                            os.path.join('src', 'truthtable.md')):
            logging.info(f'Wokwi project {wokwi_id} has a truthtable included, will test!')
            install_wokwi_testing(wokwi_id)
        
        
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
            if '*' in filename:
                logging.error("* not allowed, please specify each file")
                exit(1)
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


def harden():
    # requires PDK, PDK_ROOT, OPENLANE_ROOT & OPENLANE_IMAGE_NAME to be set in local environment
    harden_cmd = 'docker run --rm -v $OPENLANE_ROOT:/openlane -v $PDK_ROOT:$PDK_ROOT -v $(pwd):/work -e PDK=$PDK -e PDK_ROOT=$PDK_ROOT -u $(id -u $USER):$(id -g $USER) $OPENLANE_IMAGE_NAME /bin/bash -c "./flow.tcl -overwrite -design /work/src -run_path /work/runs -tag wokwi"'
    env = os.environ.copy()
    p = subprocess.run(harden_cmd, shell=True, env=env)
    if p.returncode != 0:
        logging.error("harden failed")
        exit(1)
