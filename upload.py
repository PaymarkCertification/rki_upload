from selenium import webdriver
from alive_progress import alive_bar
import time
import os
import glob
from tkinter import Tk
from logUtil import Logs
from jiraUtil import JiraServiceDesk
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
PUSER = conf.get("proxy", "username")
PPASSWORD = conf.get("proxy", "password")
RKIADDRESS = conf.get("rki", "address")
SERVICEID = int(conf.get("jira","sd_id"))


# ============================================
# webdriver options
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
# options.add_argument('--headless') # headless option renders page differently. Copy JS doesn't work
# options.add_argument('--disable-gpu')
WAIT = 30 # timeout


# ============================================
# initialize objects
log = Logs("UploadScript").logger()
sd = JiraServiceDesk(SERVER, USERNAME, PASSWORD, proxy_user=PUSER, proxy_password=PPASSWORD)
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, WAIT)

# ============================================
# script functions
def import_result(txt: str) -> str:
    driver.find_element_by_xpath('//*[@id="PEDFile"]').send_keys(os.getcwd()+f"\{txt}")
    log.info(f"Uploading file {txt} to RKI DB")
    driver.find_element_by_xpath("/html/body/div/div[2]/form/input[2]").click()
    time.sleep(5)
    driver.find_element_by_xpath('//*[@id="btnCopy"]').click()
    cpy = Tk().clipboard_get()
    log.info("Copying clipboard item")
    return cpy
    

def check2FA()-> None:
    log.info("Checking if 2FA is presented")
    wait.until(lambda driver: driver.current_url != RKIADDRESS)
    driver.find_element_by_xpath('//*[@id="DuoAdfsAdapter"]').click()
    driver.switch_to.frame(driver.find_element_by_id('duo_iframe'))
    log.info("Switched to iframe")
    driver.find_element_by_xpath('/html/body/div/div/div[1]/div/form/div[1]/fieldset[1]/div[1]/button').click()
    log.info("Clicking 'Send me a push'")
    log.info(f'Waiting for Authentication. Timeout = {WAIT} sec')
    wait.until(lambda driver: driver.current_url == RKIADDRESS)
    log.info("2FA Successfully Authenticated")

# ============================================
log.info("Init Chrome Browser")
driver.get(RKIADDRESS)
check2FA()
tickets = sd.get_keys(SERVICEID, QUEUEID)
for ticket in tickets:
    sd.get_attachment(ticket)
    for f in glob.glob('*.dat'):
        sd.create_request_comment(ticket, import_result(f),public=False)
        # import_result(f)
    sd.delete_temp_files()
quit()




# for file in glob.glob("*.dat"):
#     import_result(file)
    