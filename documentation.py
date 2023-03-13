
class Docs():

    def __init__(self, projects, args):
        self.projects = projects
        self.args = args

    # stuff related to docs
    def build_index(self):
        logging.info("building doc index")
        with open("README_init.md") as fh:
            readme = fh.read()
        with open("README.md", 'w') as fh:
            fh.write(readme)
            fh.write("| Index | Author | Title | Type | Git Repo |\n")
            fh.write("| ----- | ------ | ------| -----| ---------|\n")
            for project in self.projects:
                if not project.is_fill():
                    fh.write(project.get_index_row())

    def update_image(self):
        cmd = "klayout -l caravel.lyp gds/user_project_wrapper.gds -r dump_pic.rb -c klayoutrc"
        logging.info(cmd)
        os.system(cmd)

    # create a json file of all the project info, this is then used by tinytapeout.com to show projects
    def dump_json(self):
        designs = []
        for project in self.projects:
            design = project.get_yaml()
            designs.append(design)

        with open(args.dump_json, "w") as fh:
            fh.write(json.dumps(designs, indent=4))
        logging.info(f'wrote json to {args.dump_json}')

    def dump_markdown(self):

        with open("doc_header.md") as fh:
            doc_header = fh.read()

        with open("doc_template.md") as fh:
            doc_template = fh.read()

        with open("INFO.md") as fh:
            doc_info = fh.read()

        with open("VERIFICATION.md") as fh:
            doc_verification = fh.read()

        with open("CREDITS.md") as fh:
            doc_credits = fh.read()

        with open(args.dump_markdown, 'w') as fh:
            fh.write(doc_header)

            for project in self.projects:
                if project.is_fill():
                    continue
                yaml_data = project.get_project_doc_yaml()

                yaml_data['index'] = project.index

                logging.info(f"building datasheet for {project}")
                # handle pictures
                yaml_data['picture_link'] = ''
                if yaml_data['picture']:
                    # skip SVG for now, not supported by pandoc
                    picture_name = yaml_data['picture']
                    if 'svg' not in picture_name:
                        picture_filename = os.path.join(project.local_dir, picture_name)
                        yaml_data['picture_link'] = '![picture]({})'.format(picture_filename)

                # now build the doc & print it
                try:
                    doc = doc_template.format(**yaml_data)
                    fh.write(doc)
                    fh.write("\n\pagebreak\n")
                except IndexError:
                    logging.warning("missing pins in info.yaml, skipping")

            # ending
            fh.write(doc_info)
            fh.write("\n\pagebreak\n")
            fh.write(doc_verification)
            fh.write("\n\pagebreak\n")
            fh.write(doc_credits)

        logging.info(f'wrote markdown to {args.dump_markdown}')

        if args.dump_pdf:
            pdf_cmd = f'pandoc --toc --toc-depth 2 --pdf-engine=xelatex -i {args.dump_markdown} -o {args.dump_pdf}'
            logging.info(pdf_cmd)
            p = subprocess.run(pdf_cmd, shell=True)
            if p.returncode != 0:
                logging.error("pdf command failed")

    def build_hugo_content(self):
        hugo_root = args.build_hugo_content
        hugo_images = os.path.join(hugo_root, 'images')
        shutil.rmtree(hugo_root)
        os.makedirs(hugo_root)
        os.makedirs(hugo_images)

        with open("hugo_template.md") as fh:
            doc_template = fh.read()

        with open("hugo_index_template.md") as fh:
            index_template = fh.read()

        # copy image
        shutil.copyfile('tinytapeout.png', os.path.join(hugo_images, 'tinytapeout.png'))

        # index page
        logging.info("building pages - can take a minute as fetching latest GDS action URLs for all projects")
        with open(os.path.join(hugo_root, '_index.md'), 'w') as fh:
            fh.write(index_template)
            fh.write('# All projects\n')
            fh.write("| Index | Title | Author |\n")
            fh.write("| ----- | ----- | -------|\n")
            for project in self.projects:
                logging.info(project)
                if not project.is_fill():
                    fh.write(project.get_hugo_row())

                    project_dir = os.path.join(hugo_root, f'{project.get_index() :03}')
                    project_image_dir = os.path.join(project_dir, 'images')
                    os.makedirs(project_dir)
                    os.makedirs(project_image_dir)
                    yaml_data = project.get_project_doc_yaml()
                    yaml_data['index'] = project.index
                    yaml_data['weight'] = project.index + 1
                    yaml_data['git_action'] = project.get_latest_action_url()
                    yaml_data['picture_link'] = ''
                    if yaml_data['picture']:
                        picture_name = yaml_data['picture']
                        picture_filename = os.path.join(project.local_dir, picture_name)
                        picture_basename = os.path.basename(picture_filename)
                        try:
                            shutil.copyfile(picture_filename, os.path.join(project_image_dir, picture_basename))
                            yaml_data['picture_link'] = f'![picture](images/{picture_basename})'
                        except FileNotFoundError:
                            yaml_data['picture_link'] = 'Image path is broken'
                    doc = doc_template.format(**yaml_data)
                    with open(os.path.join(project_dir, '_index.md'), 'w') as pfh:
                        pfh.write(doc)

