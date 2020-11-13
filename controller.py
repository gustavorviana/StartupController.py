import json
import os
import subprocess
import threading
from datetime import datetime, timedelta, time
from typing import List

from dayofweek import DayOfWeek, parse as parse_dayofweek, parse_today


class SettingsController:
    data: {}

    def __init__(self, path: str):

        if not type(path) is str or os.path.isdir(path):
            raise Exception("O arquivo de configuração é inválido!")

        self.__path = path
        self.data = None

    @property
    def path(self) -> str:
        return self.__path

    @property
    def need_load(self) -> bool:
        return self.data is None

    def load(self):
        with open(self.path) as json_file:
            self.data = json.loads(json_file.read())

    def save(self):
        with open(self.path, "w+") as json_file:
            data = json.dumps(self.data)
            json_file.write(data)

    @property
    def enabled(self) -> bool:
        return self.get('enabled', True)

    @enabled.setter
    def enabled(self, value: bool):
        self.data['enabled'] = value

    @property
    def name(self) -> str:
        return self.data['name']

    @property
    def listen_process(self):
        return self.get("listen_process", False)

    @listen_process.setter
    def listen_process(self, value: bool):
        self.data['listen_process'] = value

    @property
    def program(self) -> str:
        return self.data['program']

    @property
    def args(self) -> []:
        return self.data['args']

    def days_of_week(self) -> List[DayOfWeek]:
        if 'days' not in self.data:
            return []

        return [parse_dayofweek(day) for day in self.data['days']]

    @property
    def start_worktime(self):
        return parse_time(self.get('start_worktime'))

    @property
    def end_worktime(self):
        return parse_time(self.get('end_worktime'))

    def get(self, name: str, default=None):
        return self.data[name] if name in self.data else default


class AppController:
    _process: subprocess.Popen

    def __init__(self, app_id: str, settings: SettingsController):
        if settings.need_load:
            raise Exception("A configuração deve ser carregada antes de ser passada ao controller do aplicativo!")
        self.settings = settings
        self.id = app_id
        self.next_work_date = None

    @property
    def name(self) -> str:
        return self.settings.name

    @property
    def is_runing(self) -> bool:
        return isinstance(self.process, subprocess.Popen) and self.process.returncode is None

    @property
    def process(self):
        return self._process if hasattr(self, "_process") else None

    def start(self):

        if self.is_runing:
            raise Exception("O processo já está em funcionamento!")

        start_args = [self.settings.program]
        start_args.extend(self.settings.args)

        self.next_work_date = None
        self._process = subprocess.Popen(start_args, stdout=subprocess.PIPE)

        if not self.settings.listen_process:
            return

        out = self.process.stdout

        def listen():
            while not out.closed:
                buffer: bytes = out.readline()

                if len(buffer):
                    self.log(buffer.decode('utf-8').replace('\n', ''))
                    continue

                self.process.poll()
                self.log(f"O aplicativo foi encerrado com o código {self.process.returncode}")
                now = datetime.now()
                self.next_work_date = datetime(now.year, now.month, now.day) + timedelta(days=1)
                break

        th = threading.Thread(target=listen, daemon=True)
        th.start()

    def log(self, text: str, *prefixes):
        StartupController.write_log(text, self.name, prefixes=prefixes)

    def kill(self):
        if not self.is_runing:
            raise Exception("Não é possível iniciar matar um app que não foi iniciado!")
        self.process.kill()

    def terminate(self):
        if not self.is_runing:
            raise Exception("Não é possível iniciar matar um app que não foi iniciado!")
        self.process.terminate()

    def in_working_time(self):
        if isinstance(self.next_work_date, datetime) and datetime.now() < self.next_work_date:
            return False

        allowed_days = self.settings.days_of_week()
        if len(allowed_days) and parse_today() not in allowed_days:
            return False

        start = self.settings.start_worktime
        end = self.settings.end_worktime
        now = datetime.now().time()

        startval = start <= now if start else None
        endval = end >= now if end else None

        if startval is None and endval is None:
            return True

        if startval and endval:
            return True

        if startval is None and endval:
            return True

        return startval and endval is None


class StartupController:

    def __init__(self):
        self.__apps = {}

    @property
    def apps_dir(self):
        return make_configdir('apps')

    def __iter__(self):
        return self.__apps.values().__iter__()

    def list_configs(self) -> List[str]:
        configs_dir = f'{self.apps_dir}{os.path.sep}'
        files = []

        for item in os.listdir(configs_dir):
            if os.path.isfile(f'{configs_dir}{item}') and item.endswith('.json'):
                files.append(item[0:len(item) - 5])

        return files

    def load_app(self, app_id: str) -> AppController:
        if self.has_app(app_id):
            raise Exception("Este aplicativo já foi carregado!")

        settings = SettingsController(f"{self.apps_dir}{app_id}.json")
        settings.load()

        app = AppController(app_id, settings)
        self.__apps[app_id] = app
        return app

    def get_app(self, app_id: str) -> AppController:
        return self.__apps[app_id]

    def start_app(self, app_id: str, respect_dates=True):
        app = self.get_app(app_id) if self.has_app(app_id) else self.load_app(app_id)
        if (app.in_working_time() or not respect_dates) and app.settings.enabled:
            app.start()

        return app

    def has_app(self, app_id: str) -> bool:
        return app_id in self.__apps

    def create_config(self, name: str, program: str, days: List[DayOfWeek]):
        try:
            config = {
                "name": name,
                "program": program,
                "args": [],
                "days": [day.name for day in days]
            }
            config_path = f"{self.apps_dir}{name.replace(' ', '').lower()}.json"
            if os.path.exists(config_path):
                print(f"Não é possível criar um aplicativo com o nome {name}!")
                print("Este nome já está em uso!")
                return False
            configctl = SettingsController(config_path)
            configctl.data = config
            configctl.save()
            return True
        except Exception as ex:
            print(f"Falha ao criar arquivo de configuração. {str(ex)}")
            return False

    # noinspection PyBroadException
    @staticmethod
    def write_log(text: str, *tags, **kwargs):
        prefixes = ['STARTUP CONTROLLER']
        if 'prefixes' in kwargs:
            prefixes.extend(kwargs['prefixes'])

        text = load_tag(text, args=tags, prefixes=prefixes)

        try:
            logfile = f'{make_configdir()}log.txt'
            with open(logfile, "a+") as log:
                now = datetime.now().strftime("%d/%m/%y %H:%M:%S")
                log.write(f"[{now}] {text}\n")
        except Exception:
            pass

        print(text)


def make_configdir(*paths):
    config_dir = f'{get_config_dir()}{os.sep}startupctl'
    fullpath = os.path.join(config_dir, *paths)

    if not os.path.exists(fullpath):
        os.makedirs(fullpath)

    return f'{fullpath}{os.path.sep}'


def load_tag(text: str, *args, **kwargs):
    if 'args' in kwargs:
        args = kwargs['args']
    elif args is None:
        args = []
    tags = ""

    if 'prefixes' in kwargs:
        for pref in kwargs['prefixes']:
            tags += f"[{pref}] "

    for tag in args:
        tags += f"[{tag}] "

    return f"{tags}{text}"


def parse_time(timestr: str):
    if timestr is None:
        return None

    splited: List[str] = timestr.split(":")
    timelen = len(splited)

    if timelen > 3:
        return None

    hour = int(splited[0])
    minute = int(splited[1]) if timelen >= 2 else 0
    second = int(splited[2]) if timelen == 3 else 0

    return time(hour, minute, second)


def get_config_dir():
    from pathlib import Path
    home = str(Path.home())

    from sys import platform
    if platform == "win32":
        return os.getenv('APPDATA')

    return f'{home}/.config'
