# -*- coding: utf-8 -*-

# stdlib
import datetime     # day_tag creation
import copy         # day_tag creation

import logging
import traceback    # for logging
import time         # for logging

import codecs       # for get_config
import ConfigParser # for get_config

import re           # only used when xp_language_details is activated.
# 3rd party
import duolingo
import datadog
# selenium is also imported when xp_language_details is activated.

class MetricAggregator(object):
    """Stores metric data, format them and send them all at once to Datadog.
    """

    def __init__(self, api_key):
        self.api_key = api_key
        self.metrics = []

        MAPPING_WEEK_DAY = {1: "monday", 2:"tuesday", 3: "wednesday", 4: "thursday", 5: "friday", 6: "saturday", 7: "sunday"}
        week_day_today = datetime.date.isoweekday(datetime.date.today())
        self.day_tag = "week_day:%s.%s" %(week_day_today,MAPPING_WEEK_DAY[week_day_today])

    def add(self,metric_name, value, tags=[]):
        """Formats the metric value, adds the day_tag tag and appends it to a queue."""
        # check that tags is a list etc.
        # set default values etc.
        if type(tags) <> list:
            if type(tags) == str:
                _tags = [tags]
            else:
                logging.warning("MetricAggregator.add 'tags' argument is not a list. Defaulting to [].")
                _tags = []
        else:
            _tags = copy.deepcopy(tags)
        _tags.append(self.day_tag)

        self.metrics.append(
            {'metric': metric_name, 'points': value, 'tags': _tags})

    def flush(self, mute = False):
        """Sends all added metrics to Datadog api endpoint."""
        datadog.initialize(api_key = self.api_key, mute = mute)
        datadog.api.Metric.send(self.metrics) # takes ~ 5 seconds

        self.metrics = []

class LingoDetailCollector(object):
    """Gathers language-detailed metrics via a Selenium-driven browser.
    The get_metrics method is the interface of this class.
    """

    # def __init__(self): # could be customized to allow other browsers.
    #     from selenium import webdriver
    #     self.driver = webdriver.PhantomJS(executable_path='./webdrivers/phantomjs')
    #     self.driver.set_window_size(1120, 550)

    def __init__(self, browser, executable_path=''): # could be customized to allow other browsers.
        from selenium import webdriver
        accepted_browsers = ['Firefox', 'Chrome', 'PhantomJS']

        if browser not in accepted_browsers:
            log.error("Wrong browser name: %s. Should be one of the following:\n%s" %(browser,accepted_browsers))
            raise ValueError(browser)
        exec ("self.driver = webdriver.%s(executable_path=\'%s\')" %(browser,executable_path))
        self.browser_name = browser
        self.driver.set_window_size(1120, 550)

    def __enter__(self):
        return(self)

    def __exit__(self, exc_type, exc_value, traceback):
        self.driver.quit()
        if exc_type is not None:
            print exc_type, exc_value, traceback
            # return False # uncomment to pass exception through
        return self

    # def __del__(self):
    #     self.driver.quit()

    def _load_page(self, url, wait_time = 15, wait_class = "language-info"):
        """A wrapper around driver.get, that provides duolingo language data.
        Input: duolingo public profile url
        Output: a list of strings, containing the html_blocks of the "language-info" class sections of the page.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        self.driver.get(url)
        # makes the driver wait for the page to be rendered before accessing the source code
        lang_info = WebDriverWait(self.driver, wait_time).until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, wait_class))
                                       )
        # note: if loading errors or missing language-info class situation are possible
        # intercept them in this function.
        return([lang.get_attribute('innerHTML') for lang in lang_info])

    @staticmethod
    def _parse_lang_metrics(html_blocks):
        """Parses the output of the _load_page method to produce duolingo language metrics.
        Input: a XXX object with the content of "language-info" class sections of the duolingo profile page
        Output: a list of lists: [[metric, value, language]]"""
        # html_blocks = ['<div class="language-name">English - Level 10</div><div class="substat">Next level: 540 XP</div><div class="substat">Total XP: 2460 XP</div>']
        lang_data = []

        for html in html_blocks:
            info = html.split('</div>')

            match0 = re.match(r'<.*>(.*) - Level ([0-9]*)', info[0])
            match1 = re.match(r'.*: ([0-9]*)', info[1])
            match2 = re.match(r'.*: ([0-9]*)', info[2])

            lang_name = match0.group(1)
            lang_level, next_level, lang_xp = match0.group(2), match1.group(1), match2.group(1)

            lang_data.append({'language':lang_name, 'lang_xp': int(lang_xp),
                'lang_level': int(lang_level), 'next_level': int(next_level)})
        return(lang_data)

    def get_metrics(self,username):
        """Public interface to collect Duolingo language metrics.
        Input: username. Output: list of lists: [[metric, value, language]]"""
        #### FIX ME: more browser support. With more than one browser possible, there could be a select of the wait time of the _load_page function etc.
        html_blocks = self._load_page("https://www.duolingo.com/%s" %username)
        return(self._parse_lang_metrics(html_blocks))

class Config(object):
    CONFIG_PATH = "lingodog.conf"

    def __init__(self, config_path = None):
        if config_path is not None:
            self.config_path = config_path
        else:
            self.config_path = self.CONFIG_PATH
        self.get_config() # save the flattened config in `self.config`
        self.check_and_load_config() # passes config param to obj attr
                                     # e.g. self.api_key instead self.config.api_key

    def get_config(self):
        """Loads the config into a python dict of dicts.
        """
        conf = ConfigParser.ConfigParser()
        with codecs.open(self.config_path, 'r', encoding='utf-8') as f:
            conf.readfp(f)

        # bulk import
        config = {}
        for section in conf.sections():
            config[section]={}
            for option in conf.options(section):
                config[section][option] = conf.get(section, option)

        flat_config = {}
        for top_key in config.keys():
            for k,v in config[top_key].iteritems():
                flat_config[k] = v
        self.config = flat_config

    def check_and_load_config(self):  # config unpacking. Update this part if the conf file changes.
        # Mandatory stuff
        try:
            self.api_key = self.config['api_key']
            self.username, self.password = self.config['username'], self.config['password']
        except KeyError as e:
            print "Missing mandatory parameter in the configuration file: %s" %e
            raise

        # Optional parameters
        self.mname_total_xp = self.config.get('total_xp', 'duolingo.total_xp')
        self.mname_language_xp = self.config.get('language_xp', 'duolingo.language_xp')
        self.mname_language_level = self.config.get('language_level', 'duolingo.language_level')
        self.mname_language_xp_for_next_level = self.config.get('language_xp_for_next_level', 'duolingo.language_xp_for_next_level')

        self.logging_level = self.config.get('log_level', "INFO")
        self.log_filepath = self.config.get('log_filepath', 'lingodog.log')

        log_levels = ['DEBUG','INFO','ERROR','WARNING','CRITICAL','NOTSET']
        if self.logging_level not in log_levels:
            print("Wrong log_level: %s. log_level should be one of the following:\n%s\nDefaulting to INFO." %(self.logging_level,log_levels))
            self.logging_level = 'INFO'

        #language_detail collection
        self.language_detail_collection = self.config.get('language_details', False)
        self.browser = self.config.get('browser', None)
        self.executable_path = self.config.get('executable_path', "")

        if self.language_detail_collection:
            accepted_browsers = ['Firefox', 'Chrome', 'PhantomJS', None]
            if self.browser not in accepted_browsers:
                print "Config error: if needed check README to fix the problem. Error outlined below:."
                raise ValueError("%s. browser should be one of the following:\n%s" %(self.browser,accepted_browsers))
        else:
            print "Detailled metric collection is disabled. Only total_xp metric will be collected. Check README to learn how to activate more metrics."
        print "Your configuration passed!!!!"

def main(log_to_console=False): #config
    start = time.time()

    cf = Config()
    logging.basicConfig(level=cf.logging_level,filename=cf.log_filepath,format="%(asctime)s | %(levelname)s | line %(lineno)d | %(message)s")

    if log_to_console:
        # set up logging to console
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        # set a format which is simpler for console use
        formatter = logging.Formatter('%(levelname)s | line %(lineno)d | %(message)s')
        console.setFormatter(formatter)
        # add the handler to the root logger
        logging.getLogger('').addHandler(console)

    try:
        aggregator = MetricAggregator(cf.api_key)

        # A) Core: total xp metric

        logging.debug("Connecting to Duolingo.")
        lingo = duolingo.Duolingo(cf.username, password=cf.password) # set up
        # Sample output of get_friends()
        # [{'username': u'MartinFjoz', 'languages': [], 'points': 8390}, \
        # {'username': u'ArnaudRaut', 'languages': [], 'points': 7570}]

        friends = lingo.get_friends()
        for friend in friends: # might take ~30 seconds to complete
            aggregator.add(cf.mname_total_xp,
                        friend['points'], [friend['username']])

        logging.debug("Collected global XP for your %s friends." %len(friends))
        aggregator.flush() # intermediate flush in case any error occurs in B2)
        logging.debug("Global XP metrics collected and submitted in %s seconds." %(time.time()-start))

        # B) Optional: detailed language metrics, with Selenium and a browser

        if cf.language_detail_collection:
            logging.debug("Language detail metric collection is activated. Initialization of the browser driver.")

            # with LingoDetailCollector() as collector:
            with LingoDetailCollector(cf.browser,cf.executable_path) as collector:
                for friend in friends:
                    logging.debug("Collecting detailed metrics for friend %s." %friend)
                    lang_data = collector.get_metrics(friend['username'])
                    for lang in lang_data:
                        tags = [lang['language'], friend['username']]

                        aggregator.add(cf.mname_language_xp, lang['lang_xp'], tags)
                        aggregator.add(cf.mname_language_level, lang['lang_level'], tags)
                        aggregator.add(cf.mname_language_xp_for_next_level, lang['next_level'], tags)
                logging.debug("Collected detailed metrics. Shutting down the browser and flushing metrics.")

            aggregator.flush()

        logging.info("Metrics collected and submited in %s seconds." %(time.time()-start))

    except Exception as e:
        logging.error("An error occurred, some data might not be collected. %s" %traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
