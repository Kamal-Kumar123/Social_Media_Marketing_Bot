import requests
import json
import re
import time
from .config import payload, headers

class Api:
    def __init__(self):
        pass

    def get_home_page(self, username):
        try:
            home = str(requests.post("https://tikitoks.com/@" + username, data=json.dumps(payload), headers=headers).content)
        except Exception as e:
            print(e)
        return home

    def get_user_videos(self, username):
        videos = []
        home = self.get_home_page(username)
        home = str(home)
        matches = re.findall(r'http.+?"' , home)
        for match in matches:
            if "video" in match:
                match = str(match)
                match = match.replace('"', '')
                video = videos.append(match)

        return videos

    def get_popular_videos(self):
        videos = []
        home = str(requests.post("https://tikitoks.com/popular", data=json.dumps(payload), headers=headers).content)
        home = str(home)
        print(home)
        matches = re.findall(r'http.+?"' , home)
        for match in matches:
            if "video" in match:
                match = str(match)
                match = match.replace('"', '')
                video = videos.append(match)

    def get_video_homepage(self, url):
        home = str(requests.post(url, data=json.dumps(payload), headers=headers).content)
        home = str(home)
        return home

    def get_likes_count(self, url):
        home = str(requests.post(url, data=json.dumps(payload), headers=headers).content)
        home = str(home)
        likes = re.findall(r'video-meta-count">.+?.Like' , home)
        likes = str(likes).replace('video-meta-count">', '')
        likes = likes.replace(" Like", "")
        likes = likes.replace("['", "")
        likes = likes.replace("']", "")
        return str(likes)

    def get_comment_count(self, url):
        home = str(requests.post(url, data=json.dumps(payload), headers=headers).content)
        home = str(home)
        likes = re.findall(r'.\xc2\xb7.+?.Comment', home)
        likes = str(likes)
        likes = likes.replace("['\\xc2\\xb7 ", "")
        likes = likes.replace("\\", "")
        likes = likes.replace("xc2xb7 ", "")
        likes = likes.replace("[' ", "")
        likes = likes.replace(" Comment']", "")
        return likes

    def get_meta_title(self, url):
        home = self.get_video_homepage(url)
        home = str(home)
        likes = re.findall(r'.video-meta-title.+?.</strong>' , home)
        likes = str(likes)
        likes = likes.replace("n<strong>", "")
        likes = likes.replace("</strong>']", "")
        likes = likes.replace("[' video-meta-title", "")
        likes = likes.replace('">\\\ ', "")

        return likes

    def get_video_url(self, url):
        home = self.get_video_homepage(url)
        home = str(home)
        video_url = re.findall(r'.https://v...+?."' , home)
        try:
            video_url = video_url[0]
            video_url = str(video_url)
            video_url = video_url.replace('"', '')

        except:
            pass

        return video_url

    def download_user_video(self, video_url, filename):
        r = requests.get(video_url)
        print(r)
        with open(filename + ".mp4",'wb') as f:
            f.write(r.content)
            print("Video downloaded")

    def get_videos_hashtags(self, url):
        pass

