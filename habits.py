from dotenv import load_dotenv
load_dotenv()
from pathlib import Path  # python3 only
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
from datetime import datetime, timedelta
import os
import re
import logging
import sys
from todoist.api import TodoistAPI
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


label_to_track = 'track'

def get_todoist_token():
    return os.getenv('TODOIST_APIKEY')

def get_existio_token():
    return os.getenv('EXISTIO_APIKEY')

def tag_existio(tag):
    logger.info('tagging in exist.io: %s',tag)
    response = requests.post(
                      'https://exist.io/api/1/attributes/custom/append/',
                      headers={'Authorization':'Bearer '+get_existio_token()},
                      json={"value":tag})
    logger.info('response: %s',response.text)
    return response


def is_habit(text):
    return re.search(r'([\w|\s]*\w)\s+\[streak\s(\d+)\]', text)

def strip_streak(text):
    habit_match = is_habit(text)
    if habit_match:
        return habit_match.group(1)
    else:
        return text

def update_streak(item, streak):
    streak_num = '[streak {}]'.format(streak)
    text = re.sub(r'\[streak\s(\d+)\]', streak_num, item['content'])
    item.update(content=text)

def parse_task_id(task_url):
    #URL is in format: https://todoist.com/showTask?id=2690174754
    task_match = re.search('https:\/\/todoist.com\/showTask\?id=([0-9]+)', task_url)
    task_id = task_match.group(1)
    return task_id

def is_due(text):
    yesterday = datetime.utcnow().strftime("%a %d %b")
    return text[:10] == yesterday

def is_in_url(task, task_url):
    return int(task['id']) == int(parse_task_id(task_url))

def increment_streak(api, task_url):
    tasks = api.state['items']
    for task in tasks:
        habit_match = is_habit(task['content'])
        if is_in_url(task, task_url) and habit_match:
            streak = int(habit_match.group(2)) + 1
            update_streak(task, streak)
    api.commit()

def track_label_id(api):
    for label in api.state['labels']:
        if label['name'] == label_to_track:
            return label['id']
    return None

def track_task(api, task_url):
    logger.info("request to track task: %s",task_url)
    tasks = api.state['items']
    for task in tasks:
        if is_in_url(task, task_url) and track_label_id(api) in task['labels']:
            tag_existio(strip_streak(task['content']))

def reset_streak(api):
    tasks = api.state['items']
    for task in tasks:
        if task['due_date_utc'] and is_habit(task['content']) and is_due(task['due_date_utc']):
            update_streak(task, 0)
            date_string = task['date_string']
            task.update(date_string= date_string + ' starting tod')
    api.commit()

def main():
    TODOIST_API_TOKEN = get_todoist_token()
    EXISTIO_API_TOKEN = get_existio_token()
    if not TODOIST_API_TOKEN or not EXISTIO_API_TOKEN:
        logger.warning('Please set the API token in environment variable.')
        exit()
    api = TodoistAPI(TODOIST_API_TOKEN)
    api.sync()
    return api


if __name__ == '__main__':
    main()
