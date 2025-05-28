from dataclasses import dataclass
import datetime
import logging
from pathlib import Path
import argparse
from typing import Iterable, TypedDict
import requests
import bs4
import tqdm

PROGRAM_NAME = "syllacalc"
LOGGING_LEVELS = {"debug": logging.DEBUG, "info": logging.INFO, "warning": logging.WARNING, "error": logging.ERROR}
URL_PATTERN = "https://www.chalmers.se/en/education/your-studies/find-course-and-programme-syllabi/course-syllabus/{coursecode}/?acYear={year}%2F{next_year}"
SWE_MON_TO_NUM = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "maj": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "okt": 10,
    "nov": 11,
    "dec": 12,
}


@dataclass(frozen=True, eq=True, order=True, slots=True)
class CourseInfo:
    datetime: datetime.datetime
    code: str
    title: str

    def __str__(self):
        return f"{self.datetime.strftime('%Y-%m-%d %H:%M')} - {self.code} - {self.title}"


def parse_date(date_str: str) -> datetime.datetime:
    comps = date_str.split()
    day = int(comps[0])
    month = SWE_MON_TO_NUM[comps[1].lower()]
    year = int(comps[2])

    if comps[3] == "am":
        hour = 8
        minute = 30
    else:
        hour = 14
        minute = 0

    return datetime.datetime(year, month, day, hour, minute)


def get_url_course(coursecode: str, year: int):
    return URL_PATTERN.format(coursecode=coursecode, year=year, next_year=year + 1)


def get_soup(url: str) -> bs4.BeautifulSoup:
    with requests.get(url) as response:
        raw_page = response.text
    return bs4.BeautifulSoup(raw_page, "html.parser")


def get_main(soup: bs4.BeautifulSoup) -> bs4.BeautifulSoup:
    return soup.find("main")


def get_course_title(main: bs4.BeautifulSoup) -> str:
    title_div = main.find("div").find("h1")
    title = " ".join(title_div.get_text().split(" ")[3:])
    return title


def get_course_exam_datetimes(main: bs4.BeautifulSoup) -> list[str]:
    exam_dates = []

    exam_dates_res = main.find_all(string="Examination dates")
    for exam_date_res in exam_dates_res:
        table_div = exam_date_res.parent.parent.parent.parent.parent
        tbody = table_div.find("tbody")
        trs = tbody.find_all("tr")
        for tr in trs:
            tds = tr.find_all("td")
            if "Examination" not in tds[0].get_text():
                continue

            exam_date_td = tds[7]
            exam_date_children = list(exam_date_td.children)
            if not exam_date_children:
                continue

            dates_elems = exam_date_children[0]
            dates_strs = [parse_date(elem.get_text().strip()) for elem in dates_elems]

            exam_dates.extend(dates_strs)

    return exam_dates


def validate_course_codes(codes: Iterable[str] | str):
    logging.debug(f"Validating course codes: ({codes})")

    validated_codes = []

    for code in codes:
        if "." in code:
            file_path = Path(code)
            lines = file_path.read_text().splitlines()
            validated_codes.extend(lines)

        else:
            validated_codes.append(code)

    logging.debug(f"Validated course codes: ({validated_codes})")
    return validated_codes


def output(*args, **kwargs):
    print(*args, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--course_code", type=str, nargs="+", default=["courses.txt"])
    parser.add_argument("-y", "--year", type=int, default=2024)
    parser.add_argument(
        "-l",
        "--logging",
        choices=["info", "debug", "warning", "error"],
        default="warning",
    )
    args = parser.parse_args()

    log_level = LOGGING_LEVELS[args.logging]
    logging.basicConfig(level=log_level, format="%(message)s")

    logging.info(f"Running {PROGRAM_NAME} with args: {args}")
    course_codes = validate_course_codes(args.course_code)

    output(f"Course codes: ({', '.join(course_codes)})")
    course_infos: list[CourseInfo] = []
    pbar = tqdm.tqdm(total=len(course_codes), desc="Looking up courses: ")
    for course_code in course_codes:
        pbar.set_description(f"Looking up course {course_code}")
        url = get_url_course(course_code, args.year)
        logging.info(f"Looking up course {course_code} with url {url}")
        soup = get_soup(url)
        main = get_main(soup)
        if not main:
            logging.warning(f"Course code {course_code} not found")
            output("")
            pbar.update(1)
            continue

        title = get_course_title(soup)
        exam_datetimes = get_course_exam_datetimes(soup)

        for exam_datetime in exam_datetimes:
            course_infos.append(
                CourseInfo(
                    datetime=exam_datetime,
                    code=course_code,
                    title=title,
                )
            )

        pbar.update(1)
    pbar.close()

    if not course_infos:
        output("No courses found")
        return

    course_infos = [course_info for course_info in course_infos if course_info.datetime >= datetime.datetime.now()]
    course_infos = list(set(course_infos))
    course_infos = sorted(course_infos)

    output("Exams:")
    for course_info in course_infos:
        output(f"\t{str(course_info)}")


if __name__ == "__main__":
    main()
