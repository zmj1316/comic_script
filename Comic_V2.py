# -*- coding: utf-8 -*-
import copy
import os
import threading
import re

import sys
import traceback

from bs4 import BeautifulSoup
import requests
import Queue
import PyV8

q = Queue.Queue()

headers = {'Pragma': 'no-cache',
           'DNT': '1',
           'Accept-Encoding': 'gzip, deflate, sdch',
           'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6,zh-TW;q=0.4',
           'User-Agent': ('Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
                          ' AppleWebKit/537.36 (KHTML, like Gecko)'
                          ' Chrome/48.0.2564.103 Safari/537.36'),
           'Accept': 'image/webp,image/*,*/*;q=0.8',
           'Referer': 'http://www.dm5.com',
           'Connection': 'keep-alive',
           'Cache-Control': 'no-cache'
           }

url = 'http://www.dm5.com/manhua-grandblue/'


def Log(text):
    out = open('log.html', 'w')
    out.write(text.encode('utf-8'))
    out.close()


def url_gen(chapter='', pagenum=1):
    if pagenum == 1:
        return 'http://www.dm5.com' + chapter
    return 'http://www.dm5.com' + chapter[0:-1] + '-' + 'p%d' % pagenum + '/'


def getWithReferer(url):
    headers_ = copy.copy(headers)
    headers_['Referer'] = url
    return requests.get(url, headers=headers_)


def extract_id(chapter=''):
    try:
        res = re.search(r'/.*(\d{6}).*/', chapter).group(1)
    except Exception as E:
        print E.message
        print 'Error occurs when extract ' + chapter
        return 0
    return int(res)


def download(path, chapter='', pagenum=0):
    file_path = os.path.join(path, '%03d.jpg' % pagenum)
    if os.path.isfile(file_path):
        return
    url = url_gen(chapter, pagenum)
    myheaders = copy.copy(headers)
    myheaders['Referer'] = url
    fun = url + \
        'chapterfun.ashx?cid=%d&page=%d&key=&language=1&gtk=6' % (
            extract_id(chapter), pagenum)
    r1 = requests.get(fun, headers=myheaders)
    if r1.status_code != 200:
        return False
    with PyV8.JSContext() as ctxt:
        ctxt.enter()
        func = ctxt.eval(r1.text[4:])
        func2 = ctxt.eval(func)
    html = str(func2).split(',')[0]
    r = requests.get(html, headers=myheaders)
    if r.status_code == 404:
        print 'Blocked'
        return False
    else:
        if not os.path.exists(path):
            os.mkdir(path)
        with open(file_path, 'wb') as f:
            f.write(r.content)
            return True


def getChapterCount(chapter):
    count = 0
    while getWithReferer(url_gen(chapter, count)).status_code == 200:
        count += 1
    return count

def doChapter(chapter_turple):
    count = 0
    while download(chapter_turple[1], chapter_turple[0], count):
        count += 1
    return True

class Processor(threading.Thread):
    def __init__(self, threadname):
        threading.Thread.__init__(self, name=threadname)

    def run(self):
        while not q.empty():
            chapter = q.get()
            print chapter[1].encode('utf-8') + ' started'
            if not doChapter(chapter):
                print 'Download error'
            else:
                print self.name + ' downloaded '

if __name__ == '__main__':
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    lans = soup.find_all(attrs={'class': 'nr6 lan2'})[:-1]
    chapters = []
    for i in lans:
        chs = i.find_all(name='a')
        for c in chs:
            href = c.get('href')
            title = c.get('title')
            chapters.append((href, title.replace(' ', '')))

    chapters.reverse()
    for i in chapters[7:]:
        q.put(i)

    with PyV8.JSLocker():
        for i in xrange(5):
            p = Processor('Processor' + str(i))
            # p.setDaemon(False)
            p.start()
    while not q.empty():
        pass