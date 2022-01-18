from os import getcwd
from Util.jiraUtil import JiraServiceDesk, Transition
import json
from configparser import ConfigParser
import glob
import os
from pathlib import Path
import unittest
import pytest

conf = ConfigParser()
conf.read('config.ini')
SERVER = conf.get("jira", "server")
USERNAME = conf.get("jira", "username")
PASSWORD = conf.get("jira", "password")
QUEUEID = int(conf.get("jira", "queue_id"))
PUBLIC = bool(conf.get("jira", "public"))
PUSER = conf.get("proxy", "username")
PPASSWORD = conf.get("proxy", "password")
RKIADDRESS = conf.get("rki", "address")
SERVICEID = int(conf.get("jira","sd_id"))
DC = conf.get("proxy", "dc")

# sd = JiraServiceDesk(SERVER, USERNAME, PASSWORD)
# status=sd.get_customer_request_status('CER-8404')
# possible_status = sd.get_customer_transitions('CER-8404')
# comments = sd.get_request_comments(ticket)
# print(possible_status)

ticket_wip = 'CER-8517'
ticket_open = 'CER-8516'

def function(ticket, status:str='open'):
    try:
        ticket_status = sd.get_customer_request_status(ticket)
        if ticket_status.lower() != status.lower():
            return False
        else:
            return True 
    except:
        pass
    
def integration_function(function:callable):
    if function:
        return 'Transition'
    else:
        return 'Unable'

d = ['cer-65']
tickets = ['cer-65: dwa']
if any(d[0] in s for s in tickets):
    print('here')


# print(function(ticket_wip, 'work in progress'))

@pytest.mark.checkstatus
class TestCheckStatus:

    def test_pos_open(self) -> None:
        assert function(ticket_wip) is False

    def test_pos_wip(self) -> None:
        assert function(ticket_wip, "Work in progress")

    @pytest.mark.parametrize('status', ['random', 'closed', 'work in progress'])
    def test_neg_status_check(self, status: str) -> None:
        assert not function(ticket_open, status)

    def test_pos_function_integration(self):
        assert integration_function(function(ticket_open)) == 'Transition'
    
    @pytest.mark.parametrize('status', ['random', 'closed', 'work in progress'])
    def test_neg_function_integration(self, status):
        assert integration_function(function(ticket_open, status)) == 'Unable'
