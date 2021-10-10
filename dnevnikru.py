import enum
import requests
from datetime import date, timedelta, datetime
from bs4 import BeautifulSoup
import urllib.parse


class Defaults(enum.Enum):
    """
    Дефолтные значения для параметров и ссылок
    """
    dateFrom = date.today().strftime("%d.%m.%Y")
    dateTo = (date.today() + timedelta(days=10)).strftime("%d.%m.%Y")
    studyYear = date.today().strftime("%Y")
    day = date.today().day
    month = date.today().month
    choose = urllib.parse.quote("Показать")
    base_link = "https://schools.dnevnik.ru/"
    hw_link = "".join((base_link, "homework.aspx?school={}&tab=&studyYear={}&subject=&datefrom={}&dateto={}&choose=", choose))
    marks_link = "".join((base_link, "marks.aspx?school={}&index={}&tab=period&period={}&homebasededucation=False"))
    searchpeople_link = "".join((base_link, "school.aspx?school={}&view=members&group={}&filter=&search={}&class={}"))
    birthdays_link = "".join((base_link, "birthdays.aspx?school={}&view=calendar&action=day&day={}&month={}&group={}"))
    week_link = "https://dnevnik.ru/currentprogress/choose?userComeFromSelector=True"


class DnevnikError(Exception):
    def __init__(self, message, errors):
        super().__init__(message)
        self.errors = f'DnevnikException[{errors}]'


class Dnevnik:
    def __init__(self, login, password):
        """
        Принимает логин и пароль юзера от Дневника.ру
        :param login:
        :param password:
        """
        self.login, self.password = login, password
        self.main_session = requests.Session()
        self.main_session.headers.update({"User-Agent": "Mozilla/5.0 (Wayland; Linux x86_64) AppleWebKit/537.36 ("
                                                        "KHTML, like Gecko) Chrome/94.0.4606.72 Safari/537.36"})
        self.main_session.post('https://login.dnevnik.ru/login', data={"login": self.login, "password": self.password})
        try:
            school = self.main_session.cookies['t0']
            self.school = school
        except Exception:
            raise DnevnikError('Неверный логин или пароль!', 'LoginError')

    @staticmethod
    def save_content2(self, link, page, headers) -> BeautifulSoup:
        response = self.main_session.get(link + f"&page={page}", headers=headers).text
        soup = BeautifulSoup(response, 'lxml')
        return soup

    @staticmethod
    def html_processing(self, link, headers, class_):
        subjects = []
        result = []
        first_page = self.save_content2(self, link, page=1, headers=headers)
        check_empty_page = first_page.find('div', class_='pager') # Ищем класс pager, если None, значит всего одна страница
        if check_empty_page is not None: # Если если есть страницы то обрабатываем циклом их по одной
            number_page = first_page.find('div', class_="pager").findAll('li')
            for number in range(1, int(number_page[-1].text) + 1):
                page = self.save_content2(self, link, page=number, headers=headers) # Тут два раза одинаковый код, пока не придумал как из него сделать функцию
                table = page.find('table', class_=class_)
                all_tr = table.findAll('tr')
                for row in all_tr:
                    all_td = row.findAll('td')
                    for td in all_td:
                        if td.a is None:
                            text = td.get_text("\r\n", strip=True)
                        else:
                            text = td.a.get_text("\r\n", strip=True)
                        text = text.replace("\r\n", " ").replace("\xa0", " ")
                        result.append(text)
                subjects.append(tuple(result))
            return subjects
        else: # если страница одна
            if "Домашних заданий не найдено." in first_page.text or "Никого не найдено. Измените условия поиска." in \
                    first_page.text or "в школе именинников нет" in first_page.text: # Тут чекаем если никого не найдено
                return "Ничего не найдено"
            else: # Тут обрабатываем одну первую страницу (Например, если вызвали метод birthdays, там день рождения всего у одного человека
                # и соответственно будет всего одна страница)
                table = first_page.find('table', class_=class_)
                all_tr = table.findAll('tr')
                for row in all_tr:
                    all_td = row.findAll('td')
                    for td in all_td:
                        if td.a is None:
                            text = td.get_text("\r\n", strip=True)
                        else:
                            text = td.a.get_text("\r\n", strip=True)
                        text = text.replace("\r\n", " ").replace("\xa0", " ")
                        result.append(text)
                subjects.append(tuple(result))
            return subjects

    @staticmethod
    def get_week_response(self, session, school, weeks): # это метод для результатов недели, перенесен из класса Utils сюда
        link = Defaults.week_link.value
        data_response = session.get(link).text
        day = datetime.strptime(Defaults.dateFrom.value, "%d.%m.%Y") + timedelta(7 * weeks)
        weeks_list = []
        week = date(2021, 7, 19)
        for _ in range(35):
            week = week + timedelta(7)
            weeks_list.append(week.strftime("%d.%m.%Y"))
        for i in weeks_list:
            if day <= datetime.strptime(i, "%d.%m.%Y"):
                week = weeks_list[weeks_list.index(i) - 1]
                break
        soup = BeautifulSoup(data_response, 'lxml')
        user_id = soup.find('option')["value"]
        link = "https://dnevnik.ru/currentprogress/result/{}/{}/{}/{}?UserComeFromSelector=True".format(
            user_id, school, Defaults.studyYear.value, week)
        week_response = session.get(link).text
        return week_response

    def homework(self, datefrom=Defaults.dateFrom.value, dateto=Defaults.dateTo.value,
                 studyyear=Defaults.studyYear.value, days=10):

        if datefrom != Defaults.dateFrom.value or days != 10:
            dt = datetime.strptime(datefrom, '%d.%m.%Y')
            dateto = (dt + timedelta(days=days)).strftime("%d.%m.%Y")
        if len(datefrom) != 10 or len(dateto) != 10:
            raise DnevnikError("Неверно указаны dateto или datefrom", "Parameters error")
        if str(studyyear) not in datefrom:
            raise DnevnikError("StudyYear должен соответствовать datefrom", "Parameters error")

        link = Defaults.hw_link.value.format(self.school, studyyear, datefrom, dateto)
        hh = self.html_processing(self, link=link, headers={"Referer": link}, class_="grid gridLines vam hmw")
        return hh # В каждом методе планирую сделать красивую стандартизацию данных, пока просто возвращаеются все данные,
                  # но в некрасивом и неудобном формате

    def marks(self, index="", period=""):
        link = Defaults.marks_link.value.format(self.school, index, period)
        mm = self.html_processing(self, link=link, headers={"Referer": link}, class_="grid gridLines vam marks")
        return mm

    def searchpeople(self, group="", name="", grade=""):
        assert group in ['all', 'students', 'staff', 'director', 'management', 'teachers', 'administrators',
                         ""], "Неверная группа!"

        link = Defaults.searchpeople_link.value.format(self.school, group, name, grade)
        hh = self.html_processing(self, link=link, headers=None, class_="people grid")
        return hh

    def birthdays(self, day: int = Defaults.day.value, month: int = Defaults.month.value, group=""):
        assert group in ['all', 'students', 'staff', 'director', 'management', 'teachers', 'administrators',
                         ""], "Неверная группа!"
        assert day in list(range(1, 32)) or month not in list(range(1, 13)), "Неверный день или месяц!"

        link = Defaults.birthdays_link.value.format(self.school, day, month, group)
        bb = self.html_processing(self, link=link, headers=None, class_="people grid")
        return bb

    def week(self, info, weeks=0):
        assert info in ["themes", "attendance", "marks", "schedule", "homeworks"], \
            'info must be "themes" or "attendance" or "marks" or "schedule" or "homeworks"'
        head = "current-progress-{}".format(info)
        item = "current-progress-{}__item"
        item = item.format("list") if info != "schedule" else item.format("schedule")
        week_response = self.get_week_response(self, session=self.main_session,
                                                school=self.school, weeks=weeks)
        soup = BeautifulSoup(week_response, 'lxml')
        title = soup.findAll("h5", {"class": "h5 h5_bold"})[0].text
        h = soup.find_all("div", {"class": head})[0]
        all_li = h.findAll("li", {"class": item})
        week = [i.replace("\n", " ").strip(" ") for i in [i.text for i in all_li]]
        return [title] + week
