import time
import socket
import requests.packages.urllib3.util.connection as urllib3_cn
from typing import Optional, Dict, Any
from requests import Request, Session, Response
import hmac


# START: Force IPv4 requests
def allowed_gai_family():
    return socket.AF_INET


urllib3_cn.allowed_gai_family = allowed_gai_family
# END: Force IPv4 requests

_ENDPOINT = 'https://ftx.com/api/'
_session = Session()
api_key = open('ftx_key.txt', 'r').read()
api_secret = open('ftx_sec.txt', 'r').read()


def get(path: str, params: Optional[Dict[str, Any]] = None):
    return _request('GET', path, params=params)


def post(path: str, params: Optional[Dict[str, Any]] = None):
    return _request('POST', path, json=params)


def delete(path: str, params: Optional[Dict[str, Any]] = None):
    return _request('DELETE', path, json=params)


def _request(method: str, path: str, **kwargs):
    request = Request(method, _ENDPOINT + path, **kwargs)
    _sign_request(request)
    response = _session.send(request.prepare())
    return _process_response(response)


def _sign_request(request: Request):
    ts = int(time.time() * 1000)
    prepared = request.prepare()
    signature_payload = f'{ts}{prepared.method}{prepared.path_url}'.encode()
    if prepared.body:
        signature_payload += prepared.body
    signature = hmac.new(api_secret.encode(), signature_payload, 'sha256').hexdigest()
    request.headers['FTX-KEY'] = api_key
    request.headers['FTX-SIGN'] = signature
    request.headers['FTX-TS'] = str(ts)


def _process_response(response: Response):
    try:
        data = response.json()
    except ValueError:
        response.raise_for_status()
        raise
    else:
        if not data['success']:
            raise Exception(data['error'])
        return data['result']
