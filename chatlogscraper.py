import re
import os
from typing import List

import pandas as pd

from progressbar import ProgressBar

from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException


class ChatLogScraper(object):
    def __init__(self):
        """ Init function, defines some class variables.
        """
        self.home_url = 'http://www.perverted-justice.com/?con=full'

        # setup and compile the regular expression for later
        master_matcher = r'([\s\w\d]+)[:-]?\s(?:\(.*\s(\d+:\d+:\d+\s[AP]M)\))?:?((.*)(\s\d+:\d+\s[AP]M)|(.*))'
        self.chat_instance = re.compile(master_matcher, re.IGNORECASE)  # ignore case is not necessary but hey!

        # instantiate the firefox driver in headless mode, disable all css, images, etc
        here = os.path.dirname(os.path.realpath(__file__))
        executable = os.path.join(here, 'chromedriver')
        # set the headless cmd
        options = Options()
        options.add_argument('--headless')
        self.driver = Chrome(executable_path=executable,
                             chrome_options=options)

    def start(self) -> List[str]:
        """ Main function to be run, go to the home page, find the list of cases,
        then send a request to the scrape function to get the data from that page

        :return: list of links to scrap
        """
        print('loading main page')
        self.driver.get(self.home_url)

        main_pane = self.driver.find_element_by_id('mainbox')
        all_cases = main_pane.find_elements(By.TAG_NAME, 'li')  # every case is under an LI tag
        # we'll load the href links into an array to get later
        links = []
        for case in all_cases:
            a_tags = case.find_elements(By.TAG_NAME, 'a')
            # the first a tag, is the link that we need
            links.append(a_tags[0].get_attribute('href'))
        return links

    def scrape_page(self, page_url: str) -> List[dict]:
        """ Go to the page url, use the regular expression to extact the chatdata, store
        this into a temporary pandas data frame to be returned once the page is complete.

        :param page_url: (str) the page to scrap
        :return: pandas DataFrame of all chat instances on this page
        """
        self.driver.get(page_url)
        try:
            page_text = self.driver.find_element(By.CLASS_NAME, 'chatLog').text
        except NoSuchElementException:
            print('could not get convo for', page_url)
            return [] # some pages don't contain chats
        conversations = []

        # next, we'll run the regex on the chat-log and extract the info into a formatted pandas DF
        matches = re.findall(self.chat_instance, page_text)
        for match in matches:
            # clean up false negatives, there has to be a better way...
            if 'com Conversation' not in match[0] \
                    and 'Text Messaging' not in match[0] \
                    and 'Yahoo Instant' not in match[0]:
                username = match[0]
                if match[4]:
                    statement = match[3]
                    time = match[4]
                else:
                    statement = match[5]
                    time = match[1]
                conversations.append({
                    'username': username,
                    'statement': statement,
                    'time': time
                })
        return conversations


if __name__ == '__main__':
    chatlogscrapper = ChatLogScraper()
    conversations = []
    links = chatlogscrapper.start()

    pbar = ProgressBar(redirect_stdout=True, max_value=(len(links)))
    try:
        for index, link in enumerate(links):
            print('getting', link)
            conversations += chatlogscrapper.scrape_page(link)
            pbar.update(index)
    finally:
        conversations = pd.DataFrame(conversations)
        conversations.to_csv('output.csv', index=False)
        conversations.to_json('output.json')