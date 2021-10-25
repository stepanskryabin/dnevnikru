from dnevnikru import settings
import requests
from datetime import date, timedelta, datetime
from bs4 import BeautifulSoup


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
    def last_page(self, response):
        """
        Функция для получения номера последней страницы
        """
        try:
            soup = BeautifulSoup(response, 'lxml')
            all_pages = soup.find('div', {'class': 'pager'})
            pages = all_pages.find_all('li')
            last_page = pages[-1].text
            return last_page
        except:
            return None

    @staticmethod
    def save_content(self, response, class2):
        """
        Функция для парсинга и сохранения таблиц с сайта
        """
        soup = BeautifulSoup(response, 'lxml')
        table = soup.find('table', {'class': class2})
        content = []
        all_rows = table.findAll('tr')
        for row in all_rows:
            content.append([])
            all_cols = row.findAll('td')
            for col in all_cols:
                the_strings = [str(s) for s in col.findAll(text=True)]
                the_text = ''.join(the_strings)
                content[-1].append(the_text)
        content = [a for a in content if a != []]
        return tuple(content)

    @staticmethod
    def get_week_response(self, session, school, weeks):
        """
        Функция для получения html страницы с результатами недели
        """
        link = settings.WEEK_LINK
        data_response = session.get(link).text
        day = datetime.strptime(settings.DATEFROM, "%d.%m.%Y") + timedelta(7 * weeks)
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
            user_id, school, settings.STUDYYEAR, week)
        week_response = session.get(link).text
        return week_response

    def homework(self, datefrom=settings.DATEFROM, dateto=settings.DATETO,
                 studyyear=settings.STUDYYEAR, days=10):
        """
        Возвращает список домашней работы
        Можно передать дату начала, дату конца
        Также можно передать на сколько дней вперед показать д/з
        :param datefrom:
        :param dateto:
        :param studyyear:
        :param days:
        :return:
        """
        if datefrom != settings.DATEFROM or days != 10:
            dt = datetime.strptime(datefrom, '%d.%m.%Y')
            dateto = (dt + timedelta(days=days)).strftime("%d.%m.%Y")
        if len(datefrom) != 10 or len(dateto) != 10:
            raise DnevnikError("Неверно указаны dateto или datefrom", "Parameters error")
        if str(studyyear) not in datefrom:
            raise DnevnikError("StudyYear должен соответствовать datefrom", "Parameters error")

        link = settings.HW_LINK.format(self.school, studyyear, datefrom, dateto)
        homework_response = self.main_session.get(link, headers={"Referer": link}).text
        if "Домашних заданий не найдено." in homework_response:
            return {"homeworkCount": 0, "homework": ()}
        last_page = self.last_page(self, homework_response)

        if last_page is not None:
            subjects = []
            for page in range(1, int(last_page) + 1):
                homework_response = self.main_session.get(link + f"&page={page}", headers={"Referer": link}).text
                for i in self.save_content(self, homework_response, class2='grid gridLines vam hmw'):
                    subject = [i[2], i[0].strip(),
                               " ".join([_.strip() for _ in i[3].split()])]
                    subjects.append(tuple(subject))
            return {"homeworkCount": len(subjects), "homework": tuple(subjects)}
        if last_page is None:
            try:
                subjects = []
                for i in self.save_content(self, homework_response, class2='grid gridLines vam hmw'):
                    subject = [i[2], i[0].strip(),
                               " ".join([_.strip() for _ in i[3].split()])]
                    subjects.append(tuple(subject))
                return {"homeworkCount": len(subjects), "homework": tuple(subjects)}
            except Exception as e:
                raise DnevnikError(e, "DnevnikError")

    def marks(self, index="", period=""):
        """
        Возвращает список оценок (По умолчанию текущий период)
        Можно передать индекс (отвечает за учебный год)
        И период (Отвечает за семестр/четверть)
        :param index:
        :param period:
        :return:
        """
        link = settings.MARKS_LINK.format(self.school, index, period)
        marks_response = self.main_session.get(link, headers={"Referer": link}).text
        try:
            marks = self.save_content(self, response=marks_response, class2='grid gridLines vam marks')
            for mark in marks:
                mark[2] = mark[2].replace(" ", "")
            return tuple(marks)
        except Exception as e:
            raise DnevnikError(e, "DnevnikError")

    def searchpeople(self, group="", name="", grade=""):
        """
        Возвращает список людей и их группы
        Можно передать имя (ФИО, ФИ), группу, класс
        :param group:
        :param name:
        :param grade:
        :return:
        """
        assert group in ['all', 'students', 'staff', 'director', 'management', 'teachers', 'administrators',
                         ""], "Неверная группа!"

        link = settings.SEARCHPEOPLE_LINK.format(self.school, group, name, grade)
        searchpeople_response = self.main_session.get(link).text
        if "Никого не найдено. Измените условия поиска." in searchpeople_response:
            return {"peopleCount": 0, "people": ()}
        last_page = self.last_page(self, searchpeople_response)

        if last_page is not None:
            members = []
            for page in range(1, int(last_page) + 1):
                members_response = self.main_session.get(link + f"&page={page}").text
                for content in self.save_content(self, members_response, class2='people grid'):
                    member = [content[1].split('\n')[1], content[1].split('\n')[2]]
                    members.append(tuple(member))
            return {"peopleCount": len(members), "people": tuple(members)}
        if last_page is None:
            members = []
            try:
                for content in self.save_content(self, searchpeople_response, class2='people grid'):
                    member = [content[1].split('\n')[1], content[1].split('\n')[2]]
                    members.append(tuple(member))
                return {"peopleCount": len(members), "people": tuple(members)}
            except Exception as e:
                raise DnevnikError(e, "DnevnikError")

    def birthdays(self, day: int = settings.DAY, month: int = settings.MONTH, group=""):
        """
        Возвращает список людей у кого в этот день день рождения
        По умолчанию текущая дата
        Можно передать день (int), месяц (int), группу
        Группа class - одноклассники текущего пользователя
        :param day:
        :param month:
        :param group:
        :return:
        """
        assert group in ['all', 'students', 'staff', 'class', ''], "Неверная группа!"
        assert day in list(range(1, 32)) or month not in list(range(1, 13)), "Неверный день или месяц!"

        link = settings.BIRTHDAYS_LINK.format(self.school, day, month, group)
        birthdays_response = self.main_session.get(link).text
        if "в школе именинников нет." in birthdays_response:
            return {"peopleCount": 0, "people": ()}
        last_page = self.last_page(self, birthdays_response)

        if last_page is not None:
            birthdays = []
            for page in range(1, int(last_page) + 1):
                birthdays_response = self.main_session.get(link + f"&page={page}").text
                for i in self.save_content(self, birthdays_response, class2='people grid'):
                    birthdays.append(i[1].split('\n')[1])
            return {"birthdaysCount": len(birthdays), "birthdays": tuple(birthdays)}
        if last_page is None:
            birthdays = []
            try:
                for i in self.save_content(self, birthdays_response, class2='people grid'):
                    birthdays.append(i[1].split('\n')[1])
                return {"birthdaysCount": len(birthdays), "birthdays": tuple(birthdays)}
            except Exception as e:
                raise DnevnikError(e, "DnevnikError")

    def week(self, info="schedule", weeks=0):
        """
        info - "themes", "attendance", "marks", "schedule", "homeworks"
        weeks - По умолчанию текущая неделя
        Если передать weeks, то можно увидеть следующие/предыдущие недели
        Для предыдущих используется отрицательное число
        :param info:
        :param weeks:
        :return:
        """

        assert info in ["themes", "attendance", "marks", "schedule", "homeworks"], \
            'info must be "themes" or "attendance" or "marks" or "schedule" or "homeworks"'
        head = "current-progress-{}".format(info)
        item = "current-progress-{}__item"
        item = item.format("list") if info != "schedule" else item.format("schedule")
        week_response = self.get_week_response(self, session=self.main_session,
                                               school=self.school, weeks=weeks)
        week = {}
        soup = BeautifulSoup(week_response, 'lxml')
        student = soup.findAll("h5", {"class": "h5 h5_bold"})[0].text
        h = soup.find_all("div", {"class": head})[0]
        all_li = h.findAll("li", {"class": item})
        if info == "schedule":
            for li in all_li:
                day = li.find("div").text
                schedule = li.findAll("li")
                schedule = [x.text for x in schedule]
                week.update({day: tuple(schedule)})
            return {"student": student, "schedule": week}
        else:
            week = [i.replace("\n", " ").strip(" ") for i in [i.text for i in all_li]]
            return {"student": student, info: tuple(week)}
