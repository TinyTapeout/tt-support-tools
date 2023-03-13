import stripe, os, json
from datetime import datetime
from collections import OrderedDict
import yaml

class Orders():

    def __init__(self, config):
        self.config = config
        self.open_date = datetime.strptime(self.config['start_date'], '%Y-%m-%d')
        stripe.api_key = os.environ['STRIPE_TOKEN']
        self.orders = []


    def fetch_orders(self):
        start_id = None
        after_open_date = True

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
                            }
                        self.orders.append(order)

                # pagination
                start_id = checkout['id']
            
        # put in date order
        self.orders.reverse()
        return self.orders


    def update_project_list(self):
        project_list = {}
        # first project is the filler test project
        index = 0
        project = { 'url': self.config['filler_project'], 'status': 'active', 'fill': False }
        project_list[index] = project

        # add all the real orders
        for index, order in enumerate(self.orders):
            project = { 'url': order['git_url'], 'status': 'active', 'fill': False }
            project_list[index + 1] = project

        # fill with the filler
        for index in range(len(project_list), self.config['num_projects']):
            project = { 'url': self.config['filler_project'], 'status': 'active', 'fill': True }
            project_list[index] = project

        with open('projects.yaml', 'w') as fh:
            fh.write(yaml.dump(project_list, sort_keys=False))
            
