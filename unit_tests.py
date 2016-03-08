# -*- coding: utf-8 -*-

import unittest

from lingodog import *

class Test_Config(unittest.TestCase):

    def setUp(self):
        self.cf = Config()
    def test_getconfig(self):
        # Type and general struc
        self.assertEqual(type(self.cf.config),dict)
        for k,v in self.cf.config.iteritems():
            self.assertEqual(type(v),unicode)

    def test_check_and_load_config(self):
        # Mandatory parameters
        for key in ['api_key', 'username','password']:
            self.assertTrue(hasattr(self.cf, key))

class Test_MetricAggregator(unittest.TestCase):

    def setUp(self):
        self.aggregator = MetricAggregator("no_api_key")

    def test_obj(self):
        self.assertIn("api_key", self.aggregator.__dict__)
        self.assertIn("day_tag", self.aggregator.__dict__)
        self.assertIn("metrics", self.aggregator.__dict__)

    def test_add(self):
        metric_name, value = "test.metric", 1
        self.aggregator.add(metric_name, value,["tag1","tag:23"])
        self.aggregator.add(metric_name, value,"tag1")
        self.aggregator.add(metric_name, value,{"tag1","tag:23"})

        self.assertEqual(self.aggregator.metrics[0], {'metric': metric_name, 'points': value, 'tags': ["tag1","tag:23",self.aggregator.day_tag]})
        self.assertEqual(self.aggregator.metrics[1], {'metric': metric_name, 'points': value, 'tags': ["tag1",self.aggregator.day_tag]})
        self.assertEqual(self.aggregator.metrics[2], {'metric': metric_name, 'points': value, 'tags': [self.aggregator.day_tag]})

        self.assertRaises(ValueError, self.aggregator.flush, (self.aggregator, False)) # the api_key is wrong so it should fail.

class Test_LingoDetailCollector(unittest.TestCase):

    def test_driver_safety(self):  # make sure there are contextmanager and del methods
        # for key in ["__enter__","__exit__","__del__"]:
        for key in ["__enter__","__exit__"]:
            self.assertIn(key, LingoDetailCollector.__dict__)

    def test_parse_lang_metrics(self):
        _in = ['<div class="language-name">English - Level 10</div><div class="substat">Next level: 540 XP</div><div class="substat">Total XP: 2460 XP</div>']
        _out = [{'language':'English', 'lang_xp': 2460,'lang_level': 10, 'next_level': 540}]
        self.assertEqual(LingoDetailCollector._parse_lang_metrics(_in),_out)

    def assess_browser(self,browser, executable_path):
        """Code to test each browser"""
        self.username = Config().username

        with LingoDetailCollector(browser, executable_path) as collector:

            ######## A) testing__load_page

            url = "https://www.duolingo.com/%s"
            html_blocks = collector._load_page(url %self.username)  # if needed, try other wait times
            # General good execution and structure
            self.assertEqual(type(html_blocks), list)
            self.assertEqual(type(html_blocks[0]), unicode)
            # Content
            for keyword in ['language-name', '- Level ','Next level:','Total XP: ']:
                self.assertIn(keyword,html_blocks[0])
            self.assertEqual(3,html_blocks[0].count('</div>'))

            ######## B) test_get_metrics

            lang_data = collector.get_metrics(self.username)
            for lan in lang_data:                      # presence of all metrics + their types
                self.assertEqual(type(lang['lang_xp']), int)
                self.assertEqual(type(lang['lang_level']), int)
                self.assertEqual(type(lang['next_level']), int)

    def test_PhantomJS(self):
        self.assess_browser("PhantomJS", "./webdrivers/phantomjs")

    def test_Chrome(self):
        self.assess_browser("Chrome", "./webdrivers/chromedriver")

    def test_Firefox(self):
        self.assess_browser("Firefox","")

if __name__ == '__main__':
    unittest.main()
