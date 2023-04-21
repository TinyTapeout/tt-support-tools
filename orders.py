import stripe, os
import time
from datetime import datetime
import yaml
import requests
import pytz
import logging


class Orders():

    def __init__(self, config):
        self.config = config
        self.open_date = datetime.strptime(self.config['start_date'], '%Y-%m-%d')
        stripe.api_key = os.environ['STRIPE_TOKEN']
        self.orders = []

    def fetch_orders(self):
        orders = self.fetch_stripe_orders() + self.fetch_university_orders() + self.fetch_extra_orders()
        self.orders = sorted(orders, key=lambda d: d['time'])

    def add_extra_project(self, git_url):
        with open(self.config['extra_projects']) as fh:
            config = yaml.safe_load(fh)
        config.append({'project': {'url' : git_url, 'timestamp' : time.time()}})
        with open(self.config['extra_projects'], 'w') as fh:
            yaml.safe_dump(config, fh)
        logging.info(f"added {git_url} to {self.config['extra_projects']}")

    def fetch_extra_orders(self):
        with open(self.config['extra_projects']) as fh:
            config = yaml.safe_load(fh)

        orders = []
        for project in config:
            orders.append({
                'git_url'   : project['project']['url'],
                'email'     : None,
                'time'      : datetime.fromtimestamp(project['project']['timestamp']).replace(tzinfo=pytz.UTC)
                })

        logging.info(f"fetched extra {len(orders)} orders")
        return orders

    def fetch_university_orders(self):
        name = self.config['name']
        url = f'https://app.tinytapeout.com/api/submissions?shuttle={name}'
        r = requests.get(url)
        if r.status_code != 200:
            logging.warning("couldn't download {}".format(url))
            exit(1)

        orders = []
        for item in r.json()['items']:
            orders.append({
                'git_url'   : item['repo'],
                'email'     : None,
                'time'      : datetime.strptime(item['time'], '%Y-%m-%dT%H:%M:%S.%f%z').replace(tzinfo=pytz.UTC)
                })
        logging.info(f"fetched university {len(orders)} orders")
        return orders

    def fetch_stripe_orders(self):
        start_id = None
        after_open_date = True
        orders = []

        while after_open_date:
            checkouts = stripe.checkout.Session.list(limit=10, starting_after=start_id)

            for checkout in checkouts:
                created = datetime.fromtimestamp(checkout['created'])
                if created < self.open_date:
                    after_open_date = False

                if checkout['payment_status'] == 'paid':
                    if 'github' in checkout['metadata']:
                        git_url = checkout['metadata']['github']
                        order = {
                            'git_url' : git_url,
                            'email'   : checkout['customer_details']['email'],
                            'time'    : datetime.fromtimestamp(checkout['created']).replace(tzinfo=pytz.UTC),
                            }
                        orders.append(order)

                # pagination
                start_id = checkout['id']

        # put in date order
        logging.info(f"fetched stripe {len(orders)} orders")
        return orders

    def update_project_list(self):
        project_list = {}
        # first project is the filler test project
        index = 0
        project = {'url': self.config['filler_project'], 'status': 'active', 'fill': False}
        project_list[index] = project

        # add all the real orders
        for index, order in enumerate(self.orders):
            project = {'url': order['git_url'], 'status': 'active', 'fill': False}
            project_list[index + 1] = project

        # fill with the filler
        for index in range(len(project_list), self.config['num_projects']):
            project = {'url': self.config['filler_project'], 'status': 'active', 'fill': True}
            project_list[index] = project

        with open('projects.yaml', 'w') as fh:
            fh.write(yaml.dump(project_list, sort_keys=False))
