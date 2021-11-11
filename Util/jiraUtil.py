from atlassian import ServiceDesk
from Util.logUtil import Logs
from pathlib import Path
from enum import Enum
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
                proxy_password: str=None,
                DC: str = 'dc4'):

        self.DC = DC
        self.server = server
        self.username = username
        self.token = password
        self.log = Logs(__class__.__name__).logger()

        if proxy_user and proxy_password:
            self.log.info('Updating proxy configuration')
            self.update_proxy(proxy_user, proxy_password, DC)
            
        if username and password:
            self.log.info('Updating Auth Header')
            self.headers.update({"Authorization": f"Basic {self.base64_conv(self.username, self.token)}"})
        
        super().__init__(url=server, 
                        username=username, 
                        password=password, 
                        cloud=True, 
                        proxies=self.proxy)
        
    def update_proxy(self, user: str, password: str, dc: str, port: int=80) -> None:
        """Configures Proxy address
            @param: user: AD Login
            @param: password: AD Password
            @param: DC: DataCentre
            @param: Port: Default 80
        """
        self.proxy.update({'https':f'http://{user}:{password}@proxy_{dc}.internal.etsl.co.nz:{port}',
                            'http':f'http://{user}:{password}@proxy_{dc}.internal.etsl.co.nz:{port}'})

    @staticmethod
    def base64_conv(username: str, password: str) -> str:
        """Converts b' object or ASCII string. Returns decoded contents"""
        var = "{}:{}".format(username, password).encode('ascii')
        b64string = base64.b64encode(var).decode('ascii')
        return b64string

    def transition_issue(self, issueIdOrKey: str, transitionId: int) -> requests:
        url = f'/rest/api/3/issue/{issueIdOrKey}/transitions?expand=transitions.fields'
        headers = self.headers.copy()
        headers.update({"Content-Type":"application/json"})
        payload = json.dumps({
                        "transition": {
                            "id": transitionId}
                            })
        try:
            self.log.info(f'Transitioning issue {issueIdOrKey}')
            response = requests.request("POST", self.url + url, headers=headers, proxies=self.proxy, data=payload)
            return response
        except:
            self.log.info(f'Cannot Transition Issue. Applicable transitions available for '
            f'issue: {[i["name"] for i in self.get_transition_jira(issueIdOrKey)]}')
        

    def get_transition_jira(self, issueIdOrKey) -> json:
        """returns all available transitions for issue"""
        url = f'/rest/api/3/issue/{issueIdOrKey}/transitions'
        response = requests.request("GET", self.server + url, headers=self.headers, proxies=self.proxy)
        return response.json()['transitions']

    def get_attachment(self, issueIdOrKey: str) -> None:
        """gets all attachments for issue.
    
        """
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
        # with open(filename, 'wb') as fp: # downloads to cwd
        try:
            with open(os.getcwd()+'/temp/{}'.format(filename), 'wb') as fp: # downloads to Temp folder
                fp.write(response.content)
                self.log.info(f'Successfully downloaded: {filename}')
        except Exception as e:
            self.log.info("Error: {}. Unable to save {} file in directory".format(e, filename))

    def delete_temp_files(self) -> None:
        # extension = glob.glob(f"*{fext}")
        folder = glob.glob(os.getcwd()+'/Temp/*')
        # if len(extension) >= 1:
        if len(folder) >=1:
            self.log.info("Deleting {} file(s)".format(len(folder)))
            for enum, item in enumerate(folder, 1):
                self.log.info('{}. Deleted {}'.format(enum, item))
                if os.path.isfile(item):
                    os.remove(item)
                else:
                    self.log.info("Error: {} file not found".format(item))
        else:
            self.log.info("No files to delete.")  

    @property
    def issueCount(self) -> int:
        pass

    def get_keys(self, service_desk_id: int, queue_id: int) -> list[int]:
        issues = self.get_issues_in_queue(queue_id=queue_id, service_desk_id=service_desk_id)
        key = [issue['key'] for issue in issues['values']]
        return key
    
    def get_request_comment(self, issueIdOrKey: str):
        url = f"rest/servicedeskapi/request/{issueIdOrKey}/comment"
        response = requests.request("GET", self.server + url, headers=self.headers, proxies=self.proxy)
        return response

    

class Transition(Enum):
    """Enum class for JSD transition IDs"""
    issueRaiseInError: str = "101"
    issueResolved: str = "71"
    pending: str = "41"
    startProgress: str = "11"
    backToOpen: str =  "51"

