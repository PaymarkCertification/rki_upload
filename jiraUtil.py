from atlassian import ServiceDesk
from logUtil import Logs
import urllib
import requests
import base64
import json
import os
import glob

PUSER = 'Michael.yu'
PPASSWORD = 'Password7'
SERVER = 'https://paymark.atlassian.net'
USERNAME = 'Michael.Yu@paymark.co.nz'
PASSWORD = 'yWLx6n4RTiw28JDbiVWZ0621'


class JiraServiceDesk(ServiceDesk):
    headers = {'accept': 'application/json',
               "Authorization": "Basic <access_token>",
            #    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
            #                  'Chrome/92.0.4515.131 Safari/537.36 '
               }
    proxy = {'https': None,
             'http': None}
    def __init__(self, server: str, username: str, password: str, proxy_user:str=None, proxy_password:str=None):
        
        self.server = server
        self.username = username
        self.token = password
        self.logs = Logs(__class__.__name__).logger()
        if proxy_user and proxy_password:
            self.logs.info('Updating proxy configuration')
            self.update_proxy(proxy_user, proxy_password)
        if username and password:
            self.logs.info('Updating Auth Header')
            self.headers.update({"Authorization": f"Basic {self.base64conv(self.username, self.token)}"})
        super().__init__(url=server, username=username, password=password, cloud=True, proxies=self.proxy)
        
    def update_proxy(self, user, password, port=80) -> None:
        self.proxy.update({'https':f'http://{user}:{password}@proxy_dc4.internal.etsl.co.nz:{port}',
                            'http':f'http://{user}:{password}@proxy_dc4.internal.etsl.co.nz:{port}'})

    @staticmethod
    def base64conv(username: str, password: str) -> str:
        concat = "{}:{}".format(username, password)
        var = concat.encode('ascii')
        enc = base64.b64encode(var)
        b64string = enc.decode('ascii')
        return b64string

    def get_attachment(self, issueIdOrKey: str) -> requests:
        url = f'/rest/servicedeskapi/request/{issueIdOrKey}/attachment'
        response = requests.request("GET", self.server + url, headers=self.headers, proxies=self.proxy)
        if response.json()['values']:
            x = [x['filename'] for x in response.json()['values']]
            if len(x) <= 0:
                self.logs.info("No file(s) found in request")
            else:
                self.logs.info('Found {} attachment(s) for {}'.format(len(x), issueIdOrKey))
                for value in response.json()['values']:
                    self.logs.info(f"Downloading Attachment: {value['filename']}")
                    self.download_file(value['filename'], value['_links']['content'])

    def download_file(self, filename: str, contents: str) -> None:
        response = requests.get(contents, headers=self.headers, proxies=self.proxy)
        with open(filename, 'wb') as fp:
            fp.write(response.content)
            self.logs.info(f'Successfully downloaded {filename}')

    def delete_temp_files(self) -> None:
        glb = glob.glob("*.dat")
        if len(glb) >= 1:
            self.logs.info("Deleting {} file(s)".format(len(glb)))
            for enum, item in enumerate(glb, 1):
                self.logs.info('{}. Deleted {}'.format(enum, item))
                os.remove(item)
        else:
            self.logs.info("No files to delete.")

    @property
    def issueCount(self) -> int:
        pass

    def get_keys(self, service_desk_id: int, queue_id: int) ->list[int]:
        issues = self.get_issues_in_queue(queue_id=queue_id, service_desk_id=service_desk_id)
        key = [issue['key'] for issue in issues['values']]
        return key


if __name__ == '__main__':
    a = JiraServiceDesk(SERVER, USERNAME, PASSWORD, proxy_user=PUSER, proxy_password=PPASSWORD)
    print(a.get_customer_transitions('CER-8363'))
    a.perform_transition('CER-8363', 11)
    print(a.get_customer_transitions('CER-8363'))
# # print(a.get_keys(1, 52))
#     a.get_attachment('CER-8354')
#     a.get_attachment('CER-8357')
#     a.delete_temp_files()
#     a.new_request_comment()
#     # with open('chrome-net-export-log.json') as fp:
#     #     print(json.dumps(json.load(fp), indent=4))
