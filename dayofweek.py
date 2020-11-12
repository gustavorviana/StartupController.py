import datetime
import enum


class DayOfWeek(enum.Enum):
    # Domingo
    sunday = "sunday",
    # Segunda - feira
    monday = "monday",
    # Terça - feira
    tuesday = "tuesday",
    # Quarta - feira
    wednesday = "wednesday",
    # Quinta - feira
    thursday = "thursday",
    # Sexta - feira
    friday = "friday",
    # Sábado
    saturday = "saturday"

    def __eq__(self, other):
        return other and self.name == other.name

    @staticmethod
    def all():
        return list(map(lambda c: c, DayOfWeek))


def parse(value) -> DayOfWeek:
    if isinstance(value, str):
        return eval(f'DayOfWeek.{value}')

    days = DayOfWeek.all()
    if isinstance(value, int) and 0 <= value <= len(days):
        return days[value]

    raise Exception("DayOfWeek inválido!")


def parse_today():
    return parse(datetime.date.today().isoweekday())
