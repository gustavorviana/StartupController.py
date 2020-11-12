#!/usr/bin/python3.8
import os
import sys
import time

from controller import StartupController
from dayofweek import parse as parse_dayofweek

controller = StartupController()


def read_configs():
    for app_id in controller.list_configs():
        if controller.has_app(app_id):
            app = controller.get_app(app_id)
            app.settings.load()
            continue

        app = controller.load_app(app_id)
        if not app.settings.enabled:
            app.log("Desativado nas configurações!")
            continue


def load_apps():
    for app in controller:
        try:
            if not app.settings.enabled or app.is_runing:
                continue

            app = controller.start_app(app.id)
            if not app.is_runing:
                continue

            app.log("Executando")

            if not app.settings.listen_process:
                app.log("Os logs estão desativados!")
        except Exception as ex:
            app_name = controller.get_app(app.id).name if controller.has_app(app.id) else app.id
            # log(f"Falha ao iniciar o app {app_name}", [])
            StartupController.write_log(f"Falha ao iniciar", 'FALHA', app_name)
            StartupController.write_log(str(ex), 'FALHA', app_name)


def loader():
    while True:
        read_configs()
        load_apps()
        time.sleep(60)


def get_argument(name: str):
    if f"-{name}" not in sys.argv:
        return None

    index = sys.argv.index(f"-{name}") + 1
    if len(sys.argv) >= index >= 0:
        return sys.argv[index]

    return None


def print_day_error():
    print("Dias de funcionamento inválidos.")
    print("Os dias de funcionamento devem ser de demingo a sábado"
          "cada dia sendo representado de 1 a 7 respectivamente.")


def create_config():
    name = get_argument('name')
    program = get_argument('program')
    if name is None:
        name = input("Name: ")
    if program is None:
        program = input("Programa: ")

    if not os.path.exists(program):
        print(f"O programa \"{program}\" é inválido")
        return
    runday = []

    print("Dias de funcionamento separados por virgula (,)")
    print("Se nenhum dia for inserido, o app irá funcionar em todos os dias!")
    print("1 - Domingo")
    print("2 - Segunda")
    print("3 - Terça")
    print("4 - Quarta")
    print("5 - Quinta")
    print("6 - Sexta")
    print("7 - Sábado")

    inputday = input("Dias: ")
    inputlist = inputday.split(',')

    if len(inputday) == 0:
        if len(inputlist) > 7:
            print_day_error()
            return

        for day in inputlist:
            if not day.isnumeric():
                print_day_error()
                return
            day = int(day)
            if day < 1 or day > 7:
                print_day_error()
                return
            runday.append(parse_dayofweek(day - 1))

    created = controller.create_config(name, program, runday)

    if created:
        print("Configuração criada!")
        return

    print("Falha ao criar configuração!")


if __name__ == "__main__":
    if '--create' in sys.argv:
        create_config()
    else:
        try:
            controller.write_log("Inicializando")
            loader()
        except KeyboardInterrupt as ex:
            pass
        except BaseException as bex:
            controller.write_log(str(bex), 'ERROR')
