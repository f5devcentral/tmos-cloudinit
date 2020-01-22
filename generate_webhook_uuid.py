#! /usr/bin/env python

import requests

WEBHOOK_URL = 'https://webhook.site/token'

resp = requests.post(WEBHOOK_URL, data = {'default_status': 200, 'default_content': {}, 'default_content_type': 'application/json', 'timeout': 0 })

print resp.json()['uuid']


