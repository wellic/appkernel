import asyncio

import requests
from flask import request
from aiohttp import ClientSession
from appkernel import Model
from appkernel.configuration import config


class RequestWrapper(object):

    # todo: timeout, retry, request timing,
    # todo: post to unknown url brings to infinite time...
    def __init__(self, url: str):
        self.url = url

    def post(self, request_object: Model, stream: bool = False, timeout: int =3):
        headers = {}
        if request:
            auth_header = request.headers.get('Authorization')
            if auth_header:
                headers.update(Authorization=auth_header)
        accept_lang = request.accept_languages if request else 'en'
        headers['Accept-Language'] = accept_lang.best
        response = requests.post(self.url, data=request_object.dumps(), stream=stream, headers=headers, timeout=timeout)

        return response.status_code, Model.to_dict(response.json())

    def get(self, request_object: Model):
        pass


class HttpClientServiceProxy(object):

    def __init__(self, root_url: str):
        self.root_url = root_url.rstrip('/')

    def __getattr__(self, item):
        if isinstance(item, str):
            return RequestWrapper(f'{self.root_url}/{item}s/')


class HttpClientFactory(object):

    @staticmethod
    def get(root_url: str):
        return HttpClientServiceProxy(root_url=root_url)
