# Lingodog

A script to collect your and your friends' duolingo experience metrics and send them to your Datadog dashboards.

## Simple vs Detailed metrics

- **Simple metric**: only _total xp_ is collected. This metric is tagged by `friend` and `week_day`.
- **Detailed metrics**: _xp by language_, _language level_ and _xp required to get to the next level_ are also collected. These additional metrics are scraped from public duolingo profile pages. Thus the **selenium** module and a browser to be driven by selenium are required. These metrics are tagged by `friend`, `week_day` and `language`.

## Installation

### Project and dependencies

```
pip install datadog, duolingo-api
# pip install selenium # if you want detailed metrics
git clone https://github.com/MartiFlex/Lingodog.git
cd Lingodog/
```

### Configuration

1. Edit lingodog.conf. At least enter your datadog api_key and your duolingo username and password.
2. Run `python run_config.py` to:
  - check the config
  - run metric collection once

### Schedule metric collection

If you're running Linux, schedule a cronjob to collect metrics every 10 minutes or so:
```
(echo "*/10 * * * * $(which python) $(pwd)/lingodog.py"; crontab -l) | crontab -
```
Otherwise use _launchctl_ (Mac) or _Windows Task Scheduler_ (Windows).

## Configuration

##### Mandatory parameters

`api_key` (Datadog), `username`, `password` (Duolingo)

##### Detailed metric collection parameters

The `language_details` parameter activates detailed metric collection. If omitted, it defaults to False.

If language_details = True, browser name & executable_path are required for Selenium:
1. `browser` should exactly match one of the following names: _PhantomJS_ or _Chrome_ or _Firefox_.
2. `executable_path`:
      - Firefox: no executable needed. Just install Firefox on your machine. `executable_path = .` (or any value of your choice)
      - Chrome: install Chrome + chromedriver (https://sites.google.com/a/chromium.org/chromedriver/home). `executable_path= relative_or_absolute_path_to_your_chromedriver_file`
      - PhantomJS: just get a PhantomJS executable (here for instance: https://github.com/eugene1g/phantomjs/releases). `executable_path= relative_or_absolute_path_to_your_phantomjs_file`

Example:

```
language_details = True
browser = PhantomJS
executable_path = ./webdrivers/phantomjs
```

##### Optional parameters

- Change reporting metric names: parameters `total_xp`, `language_xp`, `language_level`, `language_xp_for_next_level`
- Change Log level and log file location: `log_level` (set it up to `DEBUG` to get more logging), `log_filepath`
