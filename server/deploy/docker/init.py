# !/usr/bin/env python
# -*- coding:utf-8 -*-

from __future__ import absolute_import

import os
import yaml
import json


def replace_key_id():
    with open("/opt/sigma-ocr/conf/local.json", 'r') as f:
        content = json.load(f)
    account_data = content['sigma'] if 'sigma' in content.keys() else content['sigmaserver']
    account, key, secret = None, None, None
    for k, v in account_data.items():
        account = k
        key = v['key']
        secret = v['secret']
        break
    with open("/opt/sigma-ocr/conf/ocr.yml") as f:
        ocr_content = yaml.load(f)
    ocr_secret = ocr_content.get('server').get('secret')
    ocr_key = ocr_content.get('server').get('secret')
    if secret != ocr_secret or key != ocr_key:
        ocr_content['server']['key'] = key
        ocr_content['server']['secret'] = secret
        ocr_content['server']['account'] = account
        with open("/opt/sigma-ocr/conf/ocr.yml", 'w') as of:
            yaml.dump(ocr_content, of, default_flow_style=False)

if __name__ == "__main__":
    replace_key_id()
