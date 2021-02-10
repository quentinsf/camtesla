# CamTesla is (c) Quentin Stafford-Fraser & Simon Moore 2021
# but distributed under the GPL v2.
# Makes use of the unofficially-documented API
# at https://tesla-api.timdorr.com
# and https://teslaapi.io
# Requires Python 3.6 or later.

import sys
import requests
import json
import time

API_HOST = "https://owner-api.teslamotors.com"
API_ROOT = f"{API_HOST}/api/1"

CLIENT_ID = "81527cff06843c8634fdc09e8ac0abefb46ac849f38fe1e431c2ef2106796384"
CLIENT_SECRET = "c7257eb71a564034f9419ee651c7d0e5f7aa6bfbd18bafb5c5c033b093bb2fa3"

# TODO: Replace the UA with "CamTesla" ?
UA = "Mozilla/5.0 (Linux; Android 10; Pixel 3 Build/QQ2A.200305.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/85.0.4183.81 Mobile Safari/537.36"
X_TESLA_USER_AGENT = "TeslaApp/3.10.9-433/adff2e065/android/10"

# default timeout in seconds
# Car can take a long time to wake up and respond.
_DEFAULT_TIMEOUT = 30


# name of default file to store the long-lived access token
_DEFAULT_ACCESS_TOKEN_FILE = "tesla_access_token.json"


class Resource(object):
    def __init__(self, url, access_token, timeout=_DEFAULT_TIMEOUT):
        self.url = url
        self.access_token = access_token
        self.timeout = timeout

    def __call__(self, *args, **kwargs):
        # Preprocess args and kwargs
        url = self.url
        for a in args:
            url += "/" + str(a)
        http_method = kwargs.pop(
            'http_method',
            'get' if not kwargs else 'post'
        ).lower()

        # From each keyword, strip one trailing underscore if it exists,
        # then send them as parameters to the API. This allows for
        # "escaping" of keywords that might conflict with Python syntax
        # or with the specially-handled keyword "http_method".
        kwargs = {(k[:-1] if k.endswith('_') else k): v for k, v in kwargs.items()}

        auth = {"Authorization": f"bearer {self.access_token}"}
        headers = auth.copy()
        # headers["User-Agent"] = "CamTesla"
        headers["user-agent"] = UA
        headers["x-tesla-user-agent"] = X_TESLA_USER_AGENT

        if http_method == 'post':
            r = requests.post(url, params=auth, headers=headers, json=kwargs, timeout=self.timeout)
        else:
            r = requests.get(url, params=kwargs, headers=headers, timeout=self.timeout)

        if r.status_code != 200:
            raise TeslaException("Received response {c} from {u}".format(c=r.status_code, u=url))
        resp = r.json()
        if type(resp) == list:
            errors = [m['error']['description'] for m in resp if 'error' in m]
            if errors:
                raise TeslaException("\n".join(errors))
        # I *think* it's always the 'response' component we need...
        return resp['response']

    def __getattr__(self, name):
        return Resource(self.url + "/" + str(name), self.access_token, timeout=self.timeout)

    __getitem__ = __getattr__


class Server(Resource):

    def __init__(
        self,
        email: str, password: str,
        timeout: int = _DEFAULT_TIMEOUT
    ):
        """
        Create a new connection to the API endpoint.
        """

        resp = requests.post(
            f"{API_HOST}/oauth/token", 
            data={
                "email": email,
                "password": password,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "password"
            }
        )
        if resp.status_code != 200:
            raise TeslaException(f"Received status code {resp.status_code} when attempting login")
        data = resp.json()

        # TODO: we should store and reuse the credentials to avoid the repeated
        # need for the username and password.
        
        super().__init__(
            API_ROOT,
            data["access_token"],
            timeout=timeout
        )
        # self.token_creation = data["created_at"]
        # self.expires_at = self.token_creation + data["expires_in"]


# Start of a Server using OAuth2 and multi-factor authentication using
# a long-lived authentication token that will most likely need to be
# stored in a file and reused
class ServerOAuth2(Resource):
    # TODO: this currently relies on already having an access token stored
    # Currently getting a long-lived token that might require multi-factor
    # authentication using:
    #   python3 tesla.py -e 'Your Email' -p 'Your Password' -f 'tesla_access_token.json'
    # from:
    #   https://github.com/enode-engineering/tesla-oauth2
    def __init__(
            self,
            tokenfile: str = _DEFAULT_ACCESS_TOKEN_FILE,
            timeout: int = _DEFAULT_TIMEOUT
    ):
        with open(tokenfile) as json_file:
            self.fulltoken = json.load(json_file)
        # TODO: check when the access token expires and renew
        super().__init__(
            API_ROOT,
            self.fulltoken['access_token'],
            timeout=timeout
        )
        
    

class TeslaException(Exception):
    pass

# -----------------------------------------------------------------------
# The following is just a demonstration:


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Syntax: {sys.argv[0]} EMAIL PASSWORD", file=sys.stderr)
        sys.exit(1)

    # The Server object represents the API connection
    s = Server(email=sys.argv[1], password=sys.argv[2])

    # 's.vehicles' represents the '/vehicles' URL within the API
    # Calling it like this executes a GET request and returns the result.
    # (Strictly, it decodes the returned JSON and returns the 'response'
    # component as Python values.
    vehicles = s.vehicles()
    
    # Assume you have a car:
    car_vin = vehicles[0]['vin']
    print("You car's VIN is", car_vin)

    # Let's get the ID so we can use it for other calls:
    car_id = vehicles[0]['id']

    # This then represents the particular endpoint for your vehicle:
    car = s.vehicles[car_id]

    # Wake up the car and repeat until it confirms:
    while True:
        print("Waiting for car to wake up...")
        data = car.wake_up(http_method="post")
        if data['state'] == 'online':
            break
        time.sleep(3)

    # Call it to get the data
    vehicle_data = car.data_request.charge_state()
    print(json.dumps(vehicle_data, indent=4))
