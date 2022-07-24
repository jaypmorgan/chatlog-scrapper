import os
import time
import platform

import pandas as pd
from progressbar import ProgressBar
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException


class CQPWebScraper(object):
    def __init__(self, username, password, corpus, queries=[], n_gram=3):
        self.home_url = 'someurl'
        self.corpus_url = corpus
        self.username = username
        self.password = password
        self.corpus = corpus
        self.queries = queries
        self.n_gram = n_gram

        # set up webdriver
        here = os.path.dirname(os.path.realpath(__file__))
        if platform.system() == 'Darwin':
            exec_name = '../lib/chromedriver-mac'
        else:
            exec_name = '../lib/chromedriver'
        executable = os.path.join(here, exec_name)
        options = Options()
        # options.add_argument('--headless')
        options.add_experimental_option('prefs', {
            "download.default_directory": r"{}/Downloads/".format(os.path.expanduser('~')),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })
        self.driver = Chrome(executable_path=executable,
                             chrome_options=options)

    def login(self):
        self.driver.get(self.home_url)

        # login input fields
        uname = self.driver.find_element_by_name('username')
        passwd = self.driver.find_element_by_name('password')
        # enter the login details and login
        uname.send_keys(self.username)
        passwd.send_keys(self.password)
        passwd.send_keys(Keys.RETURN)

    def start(self):
        self.login()
        for k, v in self.queries.items():
            for query in v:
                self.query(query)

    def query(self, query):
        self.driver.get(self.corpus_url)
        query_box = self.driver.find_element_by_name('theData').send_keys(query)
        # change the restriction
        self.driver.find_element_by_xpath("/html/body/table[1]/tbody/tr/td[2]/table[2]/tbody/tr[2]/td/form/table/tbody/tr[3]/td[2]/select/option[2]").click()
        # click the start button
        self.driver.find_element_by_xpath('/html/body/table[1]/tbody/tr/td[2]/table[2]/tbody/tr[2]/td/form/table/tbody/tr[4]/td[2]/input[1]').click()
        # change query to collocations
        self.driver.find_element_by_xpath("//select[@name='redirect']/option[@value='collocations']").click()
        self.driver.find_element_by_xpath('/html/body/table[1]/tbody/tr[2]/td[8]/input[1]').click()
        # create collocation database
        self.driver.find_element_by_xpath('/html/body/table[1]/tbody/tr[4]/th/input').click()
        # collocation controls
        self.driver.find_element_by_xpath("//select[@name='collocCalcStat']/option[@value='7']").click()
        self.driver.find_element_by_xpath("//select[@name='collocCalcEnd']/option[@value='{}']".format(str(self.n_gram))).click()
        self.driver.find_element_by_xpath("//select[@name='collocCalcBegin']/option[@value='{}']".format(str('-' + str(self.n_gram)))).click()
        # update
        self.driver.find_element_by_xpath("//select[@name='redirect']/option[@value='collocationDownload']").click()
        self.driver.find_element_by_xpath('/html/body/table[1]/tbody/tr[5]/td[4]/input').click()
        # wait for the download to finish and change the filename
        moved = False
        old_fn = os.path.expanduser('~/Downloads/collocation_list.txt')
        while not moved:
            try:
                df = self.parse_collocations_list(old_fn)
                df.to_csv(os.path.expanduser('~/Downloads/{}.csv'.format(query)), index=False)
                moved = True
                os.remove(old_fn)
            except FileNotFoundError:
                pass # try again

    def move_file(self, old, new):
        os.rename(os.path.expanduser('~/Downloads/{}'.format(old)),
                  os.path.expanduser('~/Downloads/{}'.format(new)))


    def generate_collocations(self, w_1, w_2, window=3):
        # construct query for CQPweb in its language.
        query = "{w_1} <<{window}>> {w_2}".format(w_1=w_1,
                                                  w_2=w_2,
                                                  window=window)
        self.driver.get(self.corpus_url)
        query_box = self.driver.find_element_by_name('theData').send_keys(query)
        # change the restriction
        self.driver.find_element_by_xpath("/html/body/table[1]/tbody/tr/td[2]/table[2]/tbody/tr[2]/td/form/table/tbody/tr[3]/td[2]/select/option[2]").click()
        self.driver.find_element_by_xpath('/html/body/table[1]/tbody/tr/td[2]/table[2]/tbody/tr[2]/td/form/table/tbody/tr[4]/td[2]/input[1]').click()
        # download the results for parsing
        self.driver.find_element_by_xpath("//select[@name='redirect']/option[@value='download-conc']").click()
        self.driver.find_element_by_xpath('/html/body/table[1]/tbody/tr[2]/td[8]/input[1]').click()
        self.driver.find_element_by_xpath('/html/body/table[1]/tbody/tr[2]/td/form[1]/input[1]').click()

        new_fn = os.path.expanduser('~/Downloads/{}.csv'.format(w_2))
        old_fn = os.path.expanduser('~/Downloads/concordance-download.txt')
        moved = False
        while not moved:
            try:
                df = pd.read_csv(old_fn, delimiter='\t')
                df.to_csv(new_fn, index=False)
                moved = True
                os.remove(old_fn)
            except FileNotFoundError:
                time.sleep(2)
                pass # try again
        return self.parse_concordance_list(df)

    def parse_concordance_list(self, df: str):
        return df['Context before'].str.cat(df['Query item'].str.cat(df['Context after'], sep=' '), sep=' ').tolist()

    def parse_collocations_list(self, fn: str):
        columns = ['No.',
                   'Word',
                   'Total no. in whole corpus',
                   'Expected collocate frequency',
                   'Observed collocate frequency',
                   'In no. of texts',
                   'Dice coefficient value']
        return pd.read_csv(fn, delimiter='\t', skiprows=5, header=None, names=columns, engine='python')

    def list_collocations(self, fn: str):
        df = pd.read_csv(fn)
        mean_dice = df['Dice coefficient value'].mean()
        std_dice = df['Dice coefficient value'].std()

        df['Frequency Diff'] = (df['Observed collocate frequency'] - df['Expected collocate frequency'])
        mean_diff = df['Frequency Diff'].mean()
        std_diff = df['Frequency Diff'].std()

        significant_dice = mean_dice + (std_dice**2)
        significant_diff = mean_diff + (std_diff*13)
        print(significant_diff)

        words = df[(df['Dice coefficient value'] > significant_dice) & (df['Frequency Diff'] > significant_diff)]
        return words['Word'].tolist()
if __name__ == '__main__':
    queries = {
               'explicitsex': ["i","to","a","have","it","in","be","me","that","for","the","on","do","of","like","not","and","if","get","with","what","know","so","just","is","how","can","at","when","my","but","go","up","don't","no","all","see","was","out","think","time","there","good","about","now","or","want","one","we","did","then","would","from","ok","back","make","right","really","some","take","more","this","too","tell","much","are","had","here","sure","still","will","talk","could","they","got","well","doing","where","something","say","way","your","other","let","long","as","off","only","any","them","never","anything","come","sorry","look","day","been","why","going","better","you"]}
    crawler = CQPWebScraper(username='<someusername>',
                            password='<somepassword>',
                            corpus='https://<someurl>/<somecorpus>',
                            queries=queries)
    crawler.login()
    # parse the files

    pbar = ProgressBar()
    for k, v in pbar(queries.items()):
        # pbar.set_description(str('downloading for theme: {}'.format(str(k))))
        themes_collocations = []
        for q in v:
            crawler.query(q)
            # read the collocation files to find what are the most related to this word
            filename = os.path.expanduser('~/Downloads/{}.csv').format(q)
            collocate_queries = crawler.list_collocations(filename)
            # with these matching words, perform a query to find their usage in sentences

            for word in collocate_queries:
                try:
                    if ',' in word:
                        word = word.replace(',', '\,')  # CQPweb fails if not escaped
                    if ']' in word:
                        word = word.replace(']', '\]')
                    themes_collocations += crawler.generate_collocations(q, word)
                except NoSuchElementException:  # there is a problem with the query
                    print('could not query words: {} {}'.format(q, word))

        with open('{}-theme.txt'.format(str(k)), 'w') as f:
            for collocation in themes_collocations:
                f.write(str(collocation) + '\n')
