from atlassian import ServiceDesk
from Util.logUtil import Logs
from enum import Enum
import urllib
import requests
import base64
import json
import os
import glob


class JiraServiceDesk(ServiceDesk):
    headers = {'accept': 'application/json',
               "Authorization": "Basic <access_token>",
            #    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
            #                  'Chrome/92.0.4515.131 Safari/537.36 '
                 "Content-Type": None
 }
    proxy = {'https': None,
             'http': None}

    def __init__(self, server: str,
                username: str, 
                password: str, 
                proxy_user: str=None, 
                proxy_password: str=None):
        
        self.server = server
        self.username = username
        self.token = password
        self.log = Logs(__class__.__name__).logger()
        if proxy_user and proxy_password:
            self.log.info('Updating proxy configuration')
            self.update_proxy(proxy_user, proxy_password)
            
        if username and password:
            self.log.info('Updating Auth Header')
            self.headers.update({"Authorization": f"Basic {self.base64_conv(self.username, self.token)}"})
        
        super().__init__(url=server, 
                        username=username, 
                        password=password, 
                        cloud=True, 
                        proxies=self.proxy)
        
    def update_proxy(self, user: str, password: str, dc: str ='dc4',port=80) -> None:
        self.proxy.update({'https':f'http://{user}:{password}@proxy_{dc}.internal.etsl.co.nz:{port}',
                            'http':f'http://{user}:{password}@proxy_{dc}.internal.etsl.co.nz:{port}'})

    @staticmethod
    def base64_conv(username: str, password: str) -> str:
        var = "{}:{}".format(username, password).encode('ascii')
        b64string = base64.b64encode(var).decode('ascii')
        return b64string

    def transition_issue(self, issueIdOrKey, transitionId):
        url = f'/rest/api/3/issue/{issueIdOrKey}/transitions?expand=transitions.fields'
        headers = self.headers.copy()
        headers.update({"Content-Type":"application/json"})
        payload = json.dumps({
                        "transition": {
                            "id": transitionId}
                            })
        try:
            self.log.info('Transitioning issue')
            response = requests.request("POST", self.url + url, headers=headers, proxies=self.proxy, data=payload)
            return response
        except:
            self.log.info(f'Cannot Transition Issue. Applicable transitions available for '
            f'issue: {[i["name"] for i in self.get_transition_jira(issueIdOrKey)]}')
        

    def get_transition_jira(self, issueIdOrKey) -> json:
        url = f'/rest/api/3/issue/{issueIdOrKey}/transitions'
        response = requests.request("GET", self.server + url, headers=self.headers, proxies=self.proxy)
        return response.json()['transitions']

    def get_attachment(self, issueIdOrKey: str) -> None:
        url = f'/rest/servicedeskapi/request/{issueIdOrKey}/attachment'
        response = requests.request("GET", self.server + url, headers=self.headers, proxies=self.proxy)
        if response.json()['values']:
            x = [x['filename'] for x in response.json()['values']]
            if len(x) <= 0:
                self.log.info("No file(s) found in request")
            else:
                self.log.info('Found {} attachment(s) for {}'.format(len(x), issueIdOrKey))
                for value in response.json()['values']:
                    self.log.info(f"Downloading Attachment: {value['filename']}")
                    self.download_file(value['filename'], value['_links']['content'])
        else:
            self.log.info("JSON not returned in response")

    def download_file(self, filename: str, contents: str) -> None:
        response = requests.get(contents, headers=self.headers, proxies=self.proxy)
        with open(filename, 'wb') as fp:
            fp.write(response.content)
            self.log.info(f'Successfully downloaded: {filename}')

    def delete_temp_files(self) -> None:
        extension = glob.glob("*.dat")
        if len(extension) >= 1:
            self.log.info("Deleting {} file(s)".format(len(extension)))
            for enum, item in enumerate(extension, 1):
                self.log.info('{}. Deleted {}'.format(enum, item))
                os.remove(item)
        else:
            self.log.info("No files to delete.")  

    @property
    def issueCount(self) -> int:
        pass

    def get_keys(self, service_desk_id: int, queue_id: int) ->list[int]:
        issues = self.get_issues_in_queue(queue_id=queue_id, service_desk_id=service_desk_id)
        key = [issue['key'] for issue in issues['values']]
        return key

class Transition(Enum):
    issueRaiseInError = "101"
    issueResolved = "71"
    pending = "41"
    startProgress = "11"
    backToOpen=  "51"

