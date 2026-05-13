# -*- coding: utf-8 -*-
# version 5
# developed by zk chen, refactored for in-process GUI usage

import argparse
import json
import random
import re
import time

import requests


URL_ROOT = "https://scut.yuketang.cn/"  # 按需修改域名 example:https://*****.yuketang.cn/
LEARNING_RATE = 4  # 学习速率
REQUEST_TIMEOUT = 30

LEAF_TYPE = {
    "video": 0,
    "homework": 6,
    "exam": 5,
    "recommend": 3,
    "discussion": 4,
}


class StopRequested(Exception):
    """Raised when the GUI asks the worker to stop."""


def make_headers(csrftoken, sessionid, university_id):
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/87.0.4280.67 Safari/537.36"
        ),
        "Content-Type": "application/json",
        "Cookie": (
            "csrftoken="
            + csrftoken
            + "; sessionid="
            + sessionid
            + "; university_id="
            + university_id
            + "; platform_id=3"
        ),
        "x-csrftoken": csrftoken,
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "university-id": university_id,
        "xtbz": "cloud",
    }


def _default_log(message):
    print(message, flush=True)


def _default_input(prompt):
    return input(prompt)


class VideoHelper:
    def __init__(
        self,
        csrftoken,
        sessionid,
        university_id,
        log_callback=None,
        input_callback=None,
        stop_callback=None,
        url_root=URL_ROOT,
        learning_rate=LEARNING_RATE,
    ):
        self.csrftoken = csrftoken
        self.sessionid = sessionid
        self.university_id = university_id
        self.url_root = url_root
        self.learning_rate = learning_rate
        self.headers = make_headers(csrftoken, sessionid, university_id)
        self.log_callback = log_callback or _default_log
        self.input_callback = input_callback or _default_input
        self.stop_callback = stop_callback
        self.submit_url = (
            self.url_root
            + "mooc-api/v1/lms/exercise/problem_apply/?term=latest&uv_id="
            + self.university_id
        )
        self.session = requests.Session()

    def log(self, message):
        self.log_callback(str(message))

    def check_stop(self):
        if self.stop_callback and self.stop_callback():
            raise StopRequested("任务已停止")

    def sleep(self, seconds):
        end_time = time.time() + seconds
        while time.time() < end_time:
            self.check_stop()
            time.sleep(min(0.2, end_time - time.time()))

    def get(self, url):
        self.check_stop()
        response = self.session.get(url=url, headers=self.headers, timeout=REQUEST_TIMEOUT)
        self.check_stop()
        return response

    def post(self, url, **kwargs):
        self.check_stop()
        response = self.session.post(
            url=url,
            headers=self.headers,
            timeout=REQUEST_TIMEOUT,
            **kwargs,
        )
        self.check_stop()
        return response

    def one_video_watcher(self, video_id, video_name, cid, user_id, classroomid, skuid):
        video_id = str(video_id)
        classroomid = str(classroomid)
        url = self.url_root + "video-log/heartbeat/"
        get_url = (
            self.url_root
            + "video-log/get_video_watch_progress/?cid="
            + str(cid)
            + "&user_id="
            + str(user_id)
            + "&classroom_id="
            + classroomid
            + "&video_type=video&vtype=rate&video_id="
            + video_id
            + "&snapshot=1&term=latest&uv_id="
            + self.university_id
        )
        progress = self.get(get_url)
        if_completed = "0"
        try:
            if_completed = re.search(r'"completed":(.+?),', progress.text).group(1)
        except Exception:
            pass

        if if_completed == "1":
            self.log(video_name + "已经学习完毕，跳过")
            return 1

        self.log(video_name + "，尚未学习，现在开始自动学习")
        self.sleep(2)

        video_frame = 0
        val = 0
        try:
            res_rate = json.loads(progress.text)
            tmp_rate = res_rate["data"][video_id]["rate"]
            if tmp_rate is None:
                return 0
            val = tmp_rate
            video_frame = res_rate["data"][video_id]["watch_length"]
        except Exception as e:
            self.log(e)

        timestamp = int(round(time.time() * 1000))
        heart_data = []
        while float(val) <= 0.95:
            self.check_stop()
            for i in range(3):
                heart_data.append(
                    {
                        "i": 5,
                        "et": "loadeddata",
                        "p": "web",
                        "n": "ali-cdn.xuetangx.com",
                        "lob": "cloud4",
                        "cp": video_frame,
                        "fp": 0,
                        "tp": 0,
                        "sp": 2,
                        "ts": str(timestamp),
                        "u": int(user_id),
                        "uip": "",
                        "c": cid,
                        "v": int(video_id),
                        "skuid": skuid,
                        "classroomid": classroomid,
                        "cc": video_id,
                        "d": 4976.5,
                        "pg": video_id
                        + "_"
                        + "".join(
                            random.sample("zyxwvutsrqponmlkjihgfedcba1234567890", 4)
                        ),
                        "sq": i,
                        "t": "video",
                    }
                )
                video_frame += self.learning_rate

            data = {"heart_data": heart_data}
            response = self.post(url, json=data)
            heart_data = []

            try:
                delay_time = re.search(
                    r"Expected available in(.+?)second.", response.text
                ).group(1).strip()
                self.log("由于网络阻塞，万恶的雨课堂，要阻塞" + str(delay_time) + "秒")
                self.sleep(float(delay_time) + 0.5)
                self.log("恢复工作啦～～")
                self.post(self.submit_url, data=data)
            except Exception:
                pass

            try:
                progress = self.get(get_url)
                res_rate = json.loads(progress.text)
                tmp_rate = res_rate["data"][video_id]["rate"]
                if tmp_rate is None:
                    return 0
                val = str(tmp_rate)
                moment = f"{float(val) * 100:.2f}%"
                self.log("学习进度为：\t" + moment + "%/100%")
                self.sleep(2)
            except Exception as e:
                self.log(e)

        self.log("视频" + video_id + " " + video_name + "学习完成！")
        return 1

    def get_videos_ids(self, course_name, classroom_id, course_sign):
        get_homework_ids = (
            self.url_root
            + "mooc-api/v1/lms/learn/course/chapter?cid="
            + str(classroom_id)
            + "&term=latest&uv_id="
            + self.university_id
            + "&sign="
            + course_sign
        )
        homework_ids_response = self.get(get_homework_ids)
        homework_json = json.loads(homework_ids_response.text)
        homework_dic = {}
        try:
            for chapter in homework_json["data"]["course_chapter"]:
                for section in chapter["section_leaf_list"]:
                    if "leaf_list" in section:
                        for leaf in section["leaf_list"]:
                            if leaf["leaf_type"] == LEAF_TYPE["video"]:
                                homework_dic[leaf["id"]] = leaf["name"]
                    elif section["leaf_type"] == LEAF_TYPE["video"]:
                        homework_dic[section["id"]] = section["name"]
            self.log(course_name + "共有" + str(len(homework_dic)) + "个视频喔！")
            return homework_dic
        except Exception:
            self.log("fail while getting homework_ids!!! please re-run this program!")
            raise Exception("fail while getting homework_ids!!! please re-run this program!")

    def get_user_id(self):
        user_id_url = self.url_root + "edu_admin/check_user_session/"
        id_response = self.get(user_id_url)

        try:
            payload = json.loads(id_response.text)
            user_id = payload.get("user_id")
            if user_id is None and isinstance(payload.get("data"), dict):
                user_id = payload["data"].get("user_id")
            if user_id is not None:
                return str(user_id).strip()
        except Exception:
            pass

        try:
            return re.search(r'"user_id":(.+?)}', id_response.text).group(1).strip()
        except Exception:
            self.log("也许是网路问题，获取不了user_id,请试着重新运行")
            raise Exception("也许是网路问题，获取不了user_id,请试着重新运行!!! please re-run this program!")

    def get_courses(self):
        get_classroom_id = (
            self.url_root
            + "mooc-api/v1/lms/user/user-courses/?status=1&page=1&no_page=1"
            + "&term=latest&uv_id="
            + self.university_id
        )
        classroom_id_response = self.get(get_classroom_id)
        your_courses = []
        try:
            for course in json.loads(classroom_id_response.text)["data"]["product_list"]:
                your_courses.append(
                    {
                        "course_name": course["course_name"],
                        "classroom_id": course["classroom_id"],
                        "course_sign": course["course_sign"],
                        "sku_id": course["sku_id"],
                        "course_id": course["course_id"],
                    }
                )
        except Exception:
            self.log("fail while getting classroom_id!!! please re-run this program!")
            raise Exception("fail while getting classroom_id!!! please re-run this program!")
        return your_courses

    def ask_course_number(self, your_courses):
        prompt = "你想刷哪门课呢？请输入编号。输入0表示全部课程都刷一遍"
        while True:
            self.check_stop()
            number = self.input_callback(prompt)
            if number is None:
                raise StopRequested("任务已停止")

            number = str(number).strip()
            if not number.isdigit() or int(number) > len(your_courses):
                self.log("输入不合法！")
                continue
            return int(number)

    def start_watch(self):
        user_id = self.get_user_id()
        your_courses = self.get_courses()
        if not your_courses:
            self.log("没有获取到可学习的课程")
            return

        for index, value in enumerate(your_courses):
            self.log("编号：" + str(index + 1) + " 课名：" + str(value["course_name"]))

        number = self.ask_course_number(your_courses)
        if number == 0:
            courses_to_watch = your_courses
        else:
            courses_to_watch = [your_courses[number - 1]]

        for course in courses_to_watch:
            self.check_stop()
            homework_dic = self.get_videos_ids(
                course["course_name"],
                course["classroom_id"],
                course["course_sign"],
            )
            for one_video in homework_dic.items():
                self.one_video_watcher(
                    one_video[0],
                    one_video[1],
                    course["course_id"],
                    user_id,
                    course["classroom_id"],
                    course["sku_id"],
                )

        self.log("搞定啦")


def start(
    csrftoken,
    sessionid,
    university_id,
    log_callback=None,
    input_callback=None,
    stop_callback=None,
):
    helper = VideoHelper(
        csrftoken,
        sessionid,
        university_id,
        log_callback=log_callback,
        input_callback=input_callback,
        stop_callback=stop_callback,
    )
    helper.start_watch()


def main(argv=None):
    parser = argparse.ArgumentParser(description="自动刷雨课堂视频")
    parser.add_argument("--csrftoken", type=str, required=True, help="csrftoken")
    parser.add_argument("--sessionid", type=str, required=True, help="sessionid")
    parser.add_argument("--university_id", type=str, required=True, help="university_id")
    args = parser.parse_args(argv)

    start(args.csrftoken, args.sessionid, args.university_id)


if __name__ == "__main__":
    main()
