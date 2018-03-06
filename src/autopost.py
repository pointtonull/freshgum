#!/usr/bin/env python3

"""
module description
"""


from glob import glob
from os import path
from pprint import pprint
from textwrap import dedent
from sys import exit, stdout
from subprocess import call
import json
import time
import yaml

from selenium import webdriver
import IPython

from thingies import thingies
from credentials import credentials

TIMEOUT = 5


def get_credentials():
    return credentials["user"], credentials["password"]


def safe(executor, attempts=50, fixer=lambda : None, step=1):
    for attempt in range(attempts):
        try:
            result = executor()
            return result
        except Exception as error:
            try:
                fixer()
            except Exception as fixer_error:
                print("fixer raised an execption, fix the fixer!")
                print(fixer_error)
            last_error = error
            time.sleep(step)
    else:
        raise last_error


class Gumtree:

    def __init__(self, username, password, headless=True):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('headless')
        driver = webdriver.Chrome(chrome_options=options)
        self.driver = driver
        self.username = username
        self.password = password
        self._restored = False

    def restore(self):
        print("Login by cookie injection")
        if self._restored:
            return False
        self.driver.get("https://gumtree.com")
        try:
            cookies = json.load(open("cookies.json"))
        except IOError:
            self._restored = False
            return False
        for cookie in cookies:
            if "gumtree.com" in cookie["domain"]:
                self.driver.add_cookie(cookie)
        self.driver.get("https://my.gumtree.com/manage-account/") # redirects to login
        self._restored = True

    def is_logged(self):
        return self.username in self.driver.page_source

    def login(self):
        methods = [
            self.restore,
            self.form_login,
            ]

        for method in methods:
            method()
            if self.is_logged():
                return True
        else:
            return False

    def form_login(self):
        print("Login using username-password")
        self.driver.get("https://my.gumtree.com/manage-account/") # redirects to login
        txt_email = safe(lambda: self.driver.find_element_by_id('email'))
        txt_email.send_keys(self.username)
        txt_password = safe(lambda: self.driver.find_element_by_id('fld-password'))
        txt_password.send_keys(self.password + "\n")
        for i in range(100):
            if "manage-account/" in self.driver.current_url:
                break
            elif not i % 5:
                print("Can you complete the captcha for me?")
            time.sleep(1)
        else:
            return False
        print("Thanks!")
        with open("cookies.json", "w") as file:
            json.dump(self.driver.get_cookies(), file)
        return True

    def close(self):
        self.driver.close()

    def clean(self):
        print("Cleaning old posted ads: ", end="")
        self.driver.get("https://my.gumtree.com/manage/ads")

        while ">0 adverts<" not in self.driver.page_source:
            print(".", end="")
            stdout.flush()
            safe(lambda: self.driver.find_element_by_css_selector(".mad-nav>li:nth-child(4)").click(), 5)
            safe(lambda: self.driver.find_element_by_css_selector(".btn-secondary").click(), 5)
        print(" Done")

    def post(self, thingy):
        print("Posting thingy: {title}".format(**thingy))
        self.driver.get("https://my.gumtree.com/postad")

        if "Pick up where you left off?" in self.driver.page_source:
            button_no = safe(
                lambda: self.driver.find_element_by_css_selector('input[type="button"].btn-secondary'))
            button_no.click()

        time.sleep(1)
        txt_short_description = safe(
            lambda: self.driver.find_element_by_id("post-ad_title-suggestion"))
        txt_short_description.send_keys(thingy["short_description"])

        div_category = safe(lambda: self.driver.find_element_by_css_selector(".media>.media-img-ext"))
        div_category.click()

        txt_postcode = safe(lambda: self.driver.find_element_by_id("post-ad_postcode"))
        try:
            txt_postcode.send_keys("BT6 0JA\n")
        except:
            pass

        # Sometimes the page doesn't load the rest of the form   xD
        set_title = lambda: self.driver.find_element_by_id("post-ad_title").send_keys(thingy["title"])
        try_to_fix = lambda: self.driver.find_element_by_xpath('//*[@id="submit-button-2"]').click()
        safe(set_title, 20, try_to_fix, 5)

        images = thingy["images"]
        if isinstance(images, str):
            images = sorted(glob(images))

        for image in images:
            button_add_picture = safe(
                lambda: self.driver.find_element_by_css_selector('input[type="file"]'))
            button_add_picture.send_keys(path.abspath(image))
            time.sleep(2)

        description = dedent(thingy["description"])
        txt_description = safe(lambda: self.driver.find_element_by_id("description"))
        txt_description.send_keys(description)

        txt_price = safe(lambda: self.driver.find_element_by_id("price"))
        txt_price.send_keys(thingy["price"])

        check_phone = safe(
                lambda: self.driver.find_element_by_xpath(
                    '//*[@id="post-ad-container"]/div[10]/div/div[2]/div[1]/div/div[1]/label'))
        check_phone.click()

        button_post = safe(lambda: self.driver.find_element_by_xpath('//*[@id="submit-button-2"]'))
        button_post.click()

        button_confirm = safe(
                lambda: self.driver.find_element_by_xpath('/html/body/div[2]/div/div[4]/main/div[1]/a[1]'))
        button_confirm.click()


def main():
    """
    The main function.
    """
    gumtree = Gumtree(*get_credentials(), headless=False)
    gumtree.login()
    try:
        gumtree.clean()
    except:
        print("x", end="")
        gumtree.clean()
    sorted_thingies = sorted( ((thingy["price"], thingy["title"], thingy)  for thingy in thingies), reverse=True)
    for price, title, thingy in sorted_thingies:
        try:
            gumtree.post(thingy)
        except:
            print("x", end="")
            gumtree.post(thingy)

    gumtree.driver.close()
    time.sleep(1)
    print("Closing all remaining instances")
    call(["matar", "chrome"])
    call(["matar", "chromium"])


if __name__ == "__main__":
    exit(main())
