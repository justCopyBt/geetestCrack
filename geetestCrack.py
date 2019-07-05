# -*-coding:utf-8 -*-
import base64
import random
import time
import functools
import numpy as np

from tools.selenium_spider import SeleniumSpider

from selenium.webdriver import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import PIL.Image as image
from PIL import ImageChops
from io import BytesIO


class Crack(object):
    """
    解决三代极验验证码滑块
    """
    def __init__(self):
        self.url = 'https://www.geetest.com'
        self.browser = SeleniumSpider(path="/personalwork/personal_tools_project/adbtools/chromedriver", max_window=True)
        self.wait = WebDriverWait(self.browser, 100)
        self.BORDER = 8
        self.table = []

        for i in range(256):
            if i < 40:
                self.table.append(0)
            else:
                self.table.append(1)

    def open(self):
        """
        打开浏览器,并输入查询内容
        """
        self.browser.get(self.url)
        self.browser.get(self.url + "/Sensebot/")
        time.sleep(1)
        self.browser.web_driver_wait_ruishu(10, "class", 'experience--area')
        self.browser.execute_js('document.getElementsByClassName("experience--area")[0].getElementsByTagName("div")'
                                '[2].getElementsByTagName("ul")[0].getElementsByTagName("li")[1].click()')

        time.sleep(1)
        self.browser.web_driver_wait_ruishu(10, "class", 'geetest_radar_tip')

        self.browser.execute_js('document.getElementsByClassName("geetest_radar_tip")[0].click()')

    def check_status(self):
        """
        检测是否需要滑块验证码
        :return:
        """
        self.browser.web_driver_wait_ruishu(10, "class", 'geetest_success_radar_tip_content')
        try:
            time.sleep(1)
            message = self.browser.find_element_by_class_name("geetest_success_radar_tip_content").text
            if message == "验证成功":
                return False
            else:
                return True
        except Exception as e:
            return True

    def get_images(self):
        """
        获取验证码图片
        :return: 图片的location信息
        """
        time.sleep(1)
        self.browser.web_driver_wait_ruishu(10, "class", 'geetest_canvas_slice')
        fullgb = self.browser.execute_js('document.getElementsByClassName("geetest_canvas_bg geetest_'
                                             'absolute")[0].toDataURL("image/png")')["value"]

        bg = self.browser.execute_js('document.getElementsByClassName("geetest_canvas_fullbg geetest_fade'
                                         ' geetest_absolute")[0].toDataURL("image/png")')["value"]
        return bg, fullgb

    def get_decode_image(self, filename, location_list):
        """
        解码base64数据
        """
        _, img = location_list.split(",")
        img = base64.decodebytes(img.encode())
        new_im: image.Image = image.open(BytesIO(img))
        new_im.convert("RGB")
        new_im.save(filename)

        return new_im

    def is_pixel_equal(self, img1: image.Image, img2: image.Image, x, y):
        """
        判断两个像素是否相同
        :param image1: 图片1
        :param image2: 图片2
        :param x: 位置x
        :param y: 位置y
        :return: 像素是否相同
        """

        # 取两个图片的像素点
        pix1 = img1.load()[x, y]
        pix2 = img2.load()[x, y]
        threshold = 30
        if (abs(pix1[0] - pix2[0] < threshold) and abs(pix1[1] - pix2[1] < threshold) and abs(
                pix1[2] - pix2[2] < threshold)):
            return True
        else:
            print("色差点", pix1, pix2)
            return False

    def compute_gap(self, img1, img2):
        """计算缺口偏移"""
        # 将图片修改为RGB模式
        img1 = img1.convert("RGB")
        img2 = img2.convert("RGB")

        # 计算差值
        diff = ImageChops.difference(img1, img2)

        # 灰度图
        diff = diff.convert("L")

        # 二值化
        diff = diff.point(self.table, '1')

        left = 43

        for w in range(left, diff.size[0]):
            lis = []
            for h in range(diff.size[1]):
                if diff.load()[w, h] == 1:
                    lis.append(w)
                if len(lis) > 5:
                    return w

    def get_gap(self, img1, img2):
        """
        获取缺口偏移量 这种查找方式成功率很低
        :param img1: 不带缺口图片
        :param img2: 带缺口图片
        :return:
        """

        left = 43

        # 优化 如果有4个像素都一样才视为是缺口边界
        lis = []
        for x in range(left, img1.size[0]):
            for y in range(img1.size[1]):
                if not self.is_pixel_equal(img1, img2, x, y):
                    lis.append(x)
                    if len(lis) >= 3:
                        left = x
                        return left
        return left

    def ease_out_quad(self, x):
        return 1 - (1 - x) * (1 - x)

    def ease_out_quart(self, x):
        return 1 - pow(1 - x, 4)

    def ease_out_expo(self, x):
        if x == 1:
            return 1
        else:
            return 1 - pow(2, -10 * x)

    def get_tracks_2(self, distance, seconds, ease_func):
        """
        根据轨迹离散分布生成的数学生成  # 参考文档  https://www.jianshu.com/p/3f968958af5a
        成功率很高 90% 往上
        :param distance: 缺口位置
        :param seconds:  时间
        :param ease_func: 生成函数
        :return: 轨迹数组
        """
        distance += 20
        tracks = [0]
        offsets = [0]
        for t in np.arange(0.0, seconds, 0.1):
            ease = ease_func
            offset = round(ease(t / seconds) * distance)
            tracks.append(offset - offsets[-1])
            offsets.append(offset)
        tracks.extend([-3, -2, -3, -2, -2, -2, -2, -1, -0, -1, -1, -1])
        return tracks

    def get_track(self, distance):
        """
        根据物理学生成方式   极验不能用 成功率基本为0
        :param distance: 偏移量
        :return: 移动轨迹
        """
        distance += 20
        # 移动轨迹
        track = []
        # 当前位移
        current = 0
        # 减速阈值
        mid = distance * 3 / 5
        # 计算间隔
        t = 0.5
        # 初速度
        v = 0

        while current < distance:
            if current < mid:
                # 加速度为正2
                a = 2
            else:
                # 加速度为负3
                a = -3
            # 初速度v0
            v0 = v
            # 当前速度v = v0 + at
            v = v0 + a * t
            # 移动距离x = v0t + 1/2 * a * t^2
            move = v0 * t + 0.5 * a * (t ** 2)
            # 当前位移
            current += move
            # 加入轨迹
            track.append(round(move))
        track.extend([-3, -3, -2, -2, -2, -2, -2, -1, -1, -1, -1])
        return track

    def move_to_gap(self, track):
        """移动滑块到缺口处"""
        slider = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'geetest_slider_button')))
        ActionChains(self.browser).click_and_hold(slider).perform()

        while track:
            x = track.pop(0)
            ActionChains(self.browser).move_by_offset(xoffset=x, yoffset=0).perform()
            time.sleep(0.02)

        ActionChains(self.browser).release().perform()

    def crack(self):
        num = 5  # 重试次数
        # 打开浏览器
        self.open()

        if self.check_status():
            # 保存的图片名字
            bg_filename = 'bg.png'
            fullbg_filename = 'fullbg.png'

            # 获取图片
            bg_location_base64, fullbg_location_64 = self.get_images()

            # 根据位置对图片进行合并还原
            bg_img = self.get_decode_image(bg_filename, bg_location_base64)
            fullbg_img = self.get_decode_image(fullbg_filename, fullbg_location_64)
            # 获取缺口位置
            gap = self.compute_gap(fullbg_img, bg_img)
            print('缺口位置', gap)

            track = self.get_tracks_2(gap - self.BORDER, random.randint(2, 4), self.ease_out_quart)
            print("滑动轨迹", track)
            print("滑动距离", functools.reduce(lambda x, y: x+y, track))
            self.move_to_gap(track)

            time.sleep(3)
            if not self.check_status():
                print('验证成功')
                return True
            else:
                print('验证失败')
                return False

        else:
            print("验证成功")
            return True


if __name__ == '__main__':
    print('开始验证')
    crack = Crack()
    count = 0
    for i in range(100):
        if crack.crack():
            count += 1
    print(f"成功率：{count / 100 * 100}%")
    # crack.open()
