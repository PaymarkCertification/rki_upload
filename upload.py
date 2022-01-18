from urllib.error import HTTPError
from selenium import webdriver
import time
import sys
import os
import glob
from Util.logUtil import Logs
from Util.jiraUtil import JiraServiceDesk, Transition
from configparser import ConfigParser, NoSectionError
from selenium.webdriver.support.ui import WebDriverWait

__version__ = 0.4
# ============================================
# Script configuration data
log = Logs(__name__).logger()

try:
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
except NoSectionError as e:
    log.error("Unable to load config: %s" %(e))

# ============================================
# webdriver options
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
options.add_argument('--headless') # headless option renders page differently. Copy JS doesn't work
options.add_argument('--disable-gpu')
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36')
options.add_argument('window-size=1920x1080')
WAIT_TIME = 30 # timeout

# ============================================
#containers
SUCCESSFUL = []
UNSUCCESSFUL = []
MANUAL_ACTION = []

# ============================================
# initialize objects

sd = JiraServiceDesk(SERVER, USERNAME, PASSWORD, proxy_user=PUSER, proxy_password=PPASSWORD, DC=DC)
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, WAIT_TIME)

# ============================================
# script functions
def import_result(ticket: str, pedFile: str) -> str:
    """
    Desc: Import PED Files to RKI Server
    @param: ticket: Jira ticket
    @param: pedFile: Absolute path for attachment
    
    """
    basename = os.path.basename(pedFile) # filename without path
    driver.find_element_by_xpath('//*[@id="PEDFile"]').send_keys(f"{pedFile}")
    log.info(f"Uploading file: {basename}")

    log.info('Select Element: Upload PED File')
    driver.find_element_by_xpath("/html/body/div/div[2]/form/input[2]").click() #upload button

    log.info("Waiting for upload to complete")
    wait.until(lambda driver: basename in driver.find_element_by_xpath('//*[@id="MessageHidden"]').get_attribute('value'))
    text = driver.find_element_by_xpath('//*[@id="MessageHidden"]').get_attribute('value')
    log.info("Getting Element Attribute: '{}'".format(text))

    if basename in text:
        if "Successful" in text:
            SUCCESSFUL.append(f'{ticket}: {basename}')
        else: 
            UNSUCCESSFUL.append(f'{ticket}: {basename}')
            MANUAL_ACTION.append(ticket)
        return text
        
    else:
        log.info("Text values missing from attribute.")
        return ''
    # return cpy
    
def stats(verbose: int=0) -> None:
    header = "\n>>>>>>>>>>>>-----Results-----<<<<<<<<<<<<\n" 
    footer = "\n>>>>>>>>>>>>-----------------<<<<<<<<<<<<"
    # print("Tickets Requiring Manual Action:",MANUAL_ACTION)
    try:
        total = len(SUCCESSFUL)+len(UNSUCCESSFUL) if not len(SUCCESSFUL) < 1 else None
        percent = int(len(SUCCESSFUL)/(len(SUCCESSFUL)+len(UNSUCCESSFUL)) * 100) if not len(SUCCESSFUL) < 1 else ''
        print(
    f"{header}"
    f"\nFiles Parsed: {total}\n"
    f"Success Rate: {percent}\n"
    f"{footer}"
        if not verbose else 
    f"{header}"
    f"\nFiles Parsed: {total}\n"
    f"Success Rate: {percent} %\n"
    f"Successful: {SUCCESSFUL}\n"
    f"Unsuccessful: {UNSUCCESSFUL}\n"
    f"Tickets Requiring Manual Action: {','.join(str(x) for x in set(MANUAL_ACTION))}\n"
    f"{footer}"
)
    except ZeroDivisionError as z:
        log.info(f"stats() function error: {z}")    


def screenshot(filename: str=None) -> None:
    '''
    Desc: Saves screenshot - Debugging feature for headless mode.
    @param: filename: image name
    
    '''
    from datetime import datetime
    log.info('Saving Screenshot')
    if not filename:
        dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        return driver.save_screenshot(dt_string)
    else:
        return driver.save_screenshot(filename)

def check2FA()-> None:
    '''Desc: Two Factor Authentication Flow.'''
    log.info("Checking 2FA is presented")
    try:
        wait.until(lambda driver: driver.current_url != RKIADDRESS)
        try:
            log.info("2FA Enabled. Processing 2FA Flow")
            driver.find_element_by_xpath('//*[@id="DuoAdfsAdapter"]').click()

            driver.switch_to.frame(driver.find_element_by_id('duo_iframe'))
            log.info("Switched to iframe")

            driver.find_element_by_xpath('/html/body/div/div/div[1]/div/form/div[1]/fieldset[1]/div[1]/button').click()
            log.info("Selected Element: 'Send me a push'")
            log.info(f'Waiting for Authentication. Timeout = {WAIT_TIME} sec')
            wait.until(lambda driver: driver.current_url == RKIADDRESS)
            log.info("2FA Successfully Authenticated")
        except TimeoutError:
            log.info("Request Timed Out")
            log.info("Stopping Execution")
            quit()
        except Exception as e:
            log.info("Exception Occured: {}".format(str(e)))
            log.info("Stopping Execution")
            quit()
    except Exception as e:
        log.info("Exception occured: {}".format(str(e)))
    finally:
        wait.until(lambda driver: driver.current_url == RKIADDRESS)
        log.info("Directed to import page.")

def get_folder(path: str) -> str:
    '''@param: path: filename
       @return: Folder path 
        '''
    try:
        folder = glob.glob(os.getcwd()+f'{path}*')
    except:
        print("Exception occurred")
    return folder

def check_status(ticket: str, status='open') -> bool:
    ''' @param: ticket: jira ticket
        @param: status: jira status for comparison
        @return: bool 
    '''
    try:
        ticket_status = sd.get_customer_request_status(ticket)
        if ticket_status.lower() != status.lower():
            return False
        else:
            return True 
    except:
        log.critical(f"Exception Occured with check_status()")

def status(ticket):
    """
       Desc: Checks ticket status. Proceeds depending on status. 
        -WIP - No Action taken by script
        -Open - Transition ticket to WIP, download attachment, upload items to RKI Server.
        **If any file fails in upload then ticket remains in WIP status. Otherwise transition ticket to resolve.
        @param: ticket: Jira Ticket
    """
    if check_status(ticket, status='work in progress'):
        MANUAL_ACTION.append(ticket)

    elif check_status(ticket):
        sd.transition_issue(ticket, Transition.startProgress.value) 
        sd.get_attachment(ticket)
        for pedFile in get_folder("/Temp/"):
            sd.create_request_comment(ticket, import_result(ticket, pedFile), public=PUBLIC) # public toggle [Internal/External Comment]
    
    elif any(ticket in j for j in UNSUCCESSFUL):
        MANUAL_ACTION.append(ticket)
    
    if not any(ticket in i for i in MANUAL_ACTION):
        sd.transition_issue(ticket, Transition.issueResolved.value)

def get_tickets(serviceId, queueId):
    from requests.exceptions import ProxyError
    try:
        return sd.get_keys(serviceId, queueId)
    except ProxyError:
        log.error("Cannot connect to proxy: <%s>. Check windows login details or proxy address" %(DC))
        sys_clean_up()
        
    except HTTPError:
        log.error("Unauthorized access for url <%s>. Check Jira login details or API address"%(SERVER))
        sys_clean_up()

def sys_clean_up():
        os.system("pause")
        sys.exit()
# ============================================
# Begin
if __name__=='__main__':

    tickets = get_tickets(SERVICEID, QUEUEID)
    # tickets = sd.get_keys(SERVICEID, QUEUEID)
    log.info("Ticket(s) in queue: {}\n{}".format(len(tickets), tickets))
    if len(tickets) >=1:
        log.info("Init Chrome Browser")
        driver.get(RKIADDRESS)
        check2FA()
        for ticket in tickets:
            status(ticket)
            sd.delete_temp_files()
        driver.quit()
        
        stats(verbose=1)
        os.system("pause")
        quit()
        
    else:
        log.info("No issues found. Stopping Execution")
        sys_clean_up()
