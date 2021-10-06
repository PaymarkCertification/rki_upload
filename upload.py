from selenium import webdriver
import time
import os
import glob
from Util.logUtil import Logs
from Util.jiraUtil import JiraServiceDesk, Transition
from configparser import ConfigParser
from selenium.webdriver.support.ui import WebDriverWait


# ============================================
# Script configuration data
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
Y = []
N = []

# ============================================
# initialize objects
log = Logs("UploadScript").logger()
sd = JiraServiceDesk(SERVER, USERNAME, PASSWORD, proxy_user=PUSER, proxy_password=PPASSWORD)
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, WAIT_TIME)

# ============================================
# script functions
def import_result(ticket: str, pedFile: str) -> str:
    driver.find_element_by_xpath('//*[@id="PEDFile"]').send_keys(os.getcwd()+f"\{pedFile}")
    log.info(f"Uploading file: {pedFile}")

    driver.find_element_by_xpath("/html/body/div/div[2]/form/input[2]").click()
    log.info('Select Element: //*[@id="btnCopy"]')
    
    log.info("Init Sleep. 5 Seconds.")
    time.sleep(5) # assumes each file takes less than 5 seconds to upload.
    driver.find_element_by_xpath('//*[@id="btnCopy"]').click()
    # cpy = Tk().clipboard_get()
    text = driver.find_element_by_xpath('//*[@id="MessageHidden"]').get_attribute('value')
    log.info("Getting Element Attribute: '{}'".format(text))
    if pedFile in text:
        if "Successful" in text:
            Y.append(f'{ticket}: {pedFile}')
        else: 
            N.append(f'{ticket}: {pedFile}')
        return text
        
    else:
        log.info("Text values missing from attribute.")
        return ''
    # return cpy
    
def stats(verbose: int=0) -> None:
    header = "\n>>>>>>>>>>>>-----Results-----<<<<<<<<<<<<\n" 
    footer = "\n>>>>>>>>>>>>-----------------<<<<<<<<<<<<"
    total = len(Y)+len(N)
    percent = int(len(Y)/(len(Y)+len(N)) * 100)
    print(
        f"{header}"
        f"\nFiles Parsed: {total}\n"
        f"Success Rate: {percent}\n"
        f"{footer}"
        if not verbose else 
        f"{header}"
        f"\nFiles Parsed: {total}\n"
        f"Success Rate: {percent}%\n"
        f"Successful: {Y}\n"
        f"Unsuccessful: {N}\n"
        f"{footer}"
    )

def screenshot(filename: str=None) -> None:
    from datetime import datetime
    log.info('Saving Screenshot')
    if not filename:
        dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        return driver.save_screenshot(dt_string)
    else:
        return driver.save_screenshot(filename)

def check2FA()-> None:
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

    
# ============================================
# Begin
if __name__=='__main__':

    tickets = sd.get_keys(SERVICEID, QUEUEID)
    log.info("Ticket(s) in queue: {}\n{}".format(len(tickets), tickets))
    log.info("Init Chrome Browser")
    driver.get(RKIADDRESS)
    check2FA()
    
    if len(tickets) >=1:
        for ticket in tickets:
            sd.get_attachment(ticket)
            for f in glob.glob('*.dat'):
                sd.transition_issue(ticket, Transition.startProgress.value)
                sd.create_request_comment(ticket, import_result(ticket,f), public=PUBLIC) # public toggle [Internal/External Comment]
                sd.transition_issue(ticket, Transition.issueResolved.value)
            sd.delete_temp_files()
        driver.quit()
        stats(verbose=1)
    else:
        log.info("No issues found")
        quit()
