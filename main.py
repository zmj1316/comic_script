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
           'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.103 Safari/537.36',
           'Accept': 'image/webp,image/*,*/*;q=0.8',
           'Referer': 'http://www.1kkk.com/ch1-116859/',
           'Connection': 'keep-alive',
           'Cache-Control': 'no-cache'
           }


def url_gen(chapter = '', pagenum = 1):
    if pagenum == 1:
        return 'http://www.1kkk.com' + chapter
    return 'http://www.1kkk.com' + chapter[0:-1] + '-' + 'p%d' % pagenum + '/'


def extract_id(chapter = ''):
    try:
        res = re.search(r'/.*(\d{6}).*/', chapter).group(1)
    except Exception as E:
        print E.message
        print 'Error occurs when extract ' + chapter
        return 0
    return int(res)


def download(chapter = '', pagenum = 0):
    url = url_gen(chapter, pagenum)
    myheaders = copy.copy(headers)
    myheaders['Referer'] = url
    fun = url + 'imagefun.ashx?cid=%d&page=%d&key=&maxcount=10' % (extract_id(chapter), pagenum)
    r1 = requests.get(fun, headers=myheaders)
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
        if not os.path.exists(chapter[1:-1]):
            os.mkdir(chapter[1:-1])
        with open(os.path.join(chapter[1:-1], '%03d.jpg' % pagenum), 'wb') as f:
            f.write(r.content)
            return True


class Processor(threading.Thread):
    def __init__(self, threadname):
        threading.Thread.__init__(self, name=threadname)

    def run(self):
        while not q.empty():
            chapter, n = q.get()
            if not download(chapter, n):
                print 'Download error'
            else:
                print self.name + ' downloaded ' + chapter + str(n)


def get_range(c):
    r = requests.get(url_gen(c))
    s = re.search(u'总<span>(\\d+)</span>页', r.text).group(1)
    print s + ' pics to be added'
    return int(s)


if __name__ == '__main__':
    try:
        manga = raw_input(u'输入漫画地址'.encode("GBK"))
        while not manga.startswith('http://www.1kkk.com/') or manga.startswith('www.1kkk.com'):
            print u'地址格式错误'.encode("GBK")
            manga = raw_input(u'输入漫画地址'.encode("GBK"))
        s = BeautifulSoup(requests.get(manga).text)
        chs = s.find_all(attrs={'class': 'sy_nr1 cplist_ullg'})[1]
        chapters = chs.find_all(name='a')
        chapter_count = len(chapters)
        print u'共%d章'.encode("GBK") % chapter_count
        head = int(raw_input(u'输入起始章节号，默认为1'.encode("GBK")) or '1')
        tail = int(raw_input(u'输入结束章节号，默认为'.encode("GBK") + str(chapter_count)) or str(chapter_count))
        count = 0
        for i in chs.find_all(name='a'):
            c = i.get('href')
            count += 1
            if count < head:
                continue
            if count > tail:
                break
            for n in range(get_range(c)):
                print c + str(n + 1) + ' added'
                q.put((c, n + 1))
        with PyV8.JSLocker():
            for i in xrange(5):
                p = Processor('Processor' + str(i))
                # p.setDaemon(False)
                p.start()
        while not q.empty():
            pass
    except (KeyboardInterrupt, SystemExit):
        print u'用户中断'.encode("GBK")
        sys.exit(1)
    except Exception as e:
        traceback.print_exc()
