#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
from os import (
    listdir,
    getcwd,
    makedirs,
    rename,
)
from os.path import (
    isfile,
    isdir,
    join,
    splitext,
    basename,
)
from threading import Thread
from time import sleep
from urllib import error as request_error
from urllib.request import urlopen
import hashlib

from requests import Session
from argparse import ArgumentParser

_args = ArgumentParser()
_args.add_argument('-m', help='Method', type=str, required=False, default='')
_args.add_argument('--hide', help='Hidden', action='store_const', required=False, const=True, default=False)
# _args.add_argument('-f', help='File', type=str, required=False, default='tts.txt')
args = _args.parse_args()

configFile = './vk_key.json'
apiVersion = '5.65'
oauthUrl = 'https://oauth.vk.com/authorize?client_id={}&display=page&redirect_uri=https://oauth.vk.com/blank.html&response_type=token&v={}&scope={}'
apiUrl = 'https://api.vk.com/method/{}?v={}&access_token={}&{}'

access = (
    #notify
    1
    #friends
    + 2
    #protos
    + 4
    #audio
    + 8
    #video
    + 16
    #pages
    + 128
    #status
    + 1024
    #notes
    # -- messages
    # + 4096
    #offline
    + 65536
    #docs
    + 131072
    #groups
    + 262144
)

try:
    with open(configFile, 'rb') as _config:
        vk_config = json.loads(_config.read().decode('utf-8'))
except Exception:
    print('Error. No config file!')
    exit(1)

if not (
        isinstance(vk_config, object)
    ):
    print('error parse config')
    exit(1)

secretKey = vk_config['secret_key']
serviceKey = vk_config['service_key']
appId = vk_config['app_id']
token = vk_config['token']
uploadAlbumId = vk_config['album']

user = vk_config['user_id'] #int(input("Input you user id: \n"))

if not user or int(user) < 0:
    print('Error!')
    exit(1)

if token == '':
    code = oauthUrl.format(appId, apiVersion, access,)
    token = input("Please, go to {} and paste code here\n".format(code,))
    if token == '':
        print('token is empty!')
        exit(1)
    data = {
      "app_id": appId,
      "secret_key": secretKey,
      "service_key": serviceKey,
      "user_id": user,
      "album": uploadAlbumId,
      "token": token
    }
    _ = open(configFile, 'wb')
    _.write(json.dumps(data).encode())
    _.close()


def _safe_downloader(url, file_name):
    while True:
        try:
            response = urlopen(url)
            out_file = open(file_name, 'wb')
            out_file.write(response.read())
            return True
        except request_error.HTTPError:
            return False
        except request_error.URLError:
            sleep(1)
            pass


def request(method: str, more: str = ""):
    url = apiUrl.format(method, apiVersion, token, more)
    r = urlopen(url)
    return r.read().decode('utf-8')


if not args.hide:
    print("User: {}\nToken: {}\nUserId: {}\n".format(id, 'secret', user,))


class MultiThreads:

    threads = []

    def __init__(self):
        self.threads = []

    def addThread(self, target: callable, args: tuple):
        self.threads.append(Thread(target=target, args=args))

    def startAll(self):
        for t in self.threads:  # starting all threads
            t.start()
        for t in self.threads:  # joining all threads
            t.join()
        self.threads = []


class User:

    albums = dict()

    def _upload(self, url: str, files):

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:20.0) Gecko/20100101 Firefox/20.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }

        # url = 'http://httpbin.org/post';
        p = Session()
        q = p.request('POST', url, files=files, headers=headers)

        if q.status_code == 200:
            j = q.json()
            server = str(j['server'])
            aid = str(j['aid'])
            hash = str(j['hash'])
            photos_list = str(bytearray(j['photos_list'], 'utf-8').decode('unicode_escape'))
            params = 'server=' + server + '&album_id=' + aid + '&hash=' + hash + '&photos_list=' + photos_list
            request('photos.save', params)

    def downloadPhotos(self, album: str = '', offset: int = 0):
        if album == '':
            album = '-1_wall'
        owner_id, album_id = album.split('_') if album.find('_') > 0 else ['', '']

        path = join(getcwd(), 'vk_download_files')
        if not isdir(path):
            return False

        if album_id == '' or owner_id == '':
            print('Album or Owner is empty!')
            print('Please, paste of format <owner>_<album>. Example:' +
                  ' https://vk.com/album5962770_24571412 =>' +
                  ' (5962770_24571412 or -5962770_24571412 from groups)')
            return False
        if album_id == '000':
            album_id = 'saved'
        if album_id == '00':
            album_id = 'wall'
        if album_id == '0':
            album_id = 'profile'

        _ = 'owner_id={}&album_id={}&photo_sizes=1&offset={}&count=1000'
        response = request('photos.get', _.format(owner_id,album_id,str(offset),))
        response = json.loads(response)

        if 'response' not in response or 'count' not in response.get('response'):
            print('response error')
            return False

        response = response.get('response')
        count = response.get('count')
        if not args.hide:
            print('Find ' + str(count) + ' photos')
        if count < 1:
            return False
        items = response.get('items')
        # images = map(lambda x: x.get('sizes')[-1], items)
        i = 1
        _items = [{'items': len(items)}]
        threads = MultiThreads()
        dn = join(path, owner_id, album_id)
        if not isdir(dn) and not (makedirs(dn, 0o777, True) or isdir(dn)):
            print('mkdir {} error!'.format(dn))
            exit(1)
        for f in items:
            src = f.get('sizes')[-1].get('src')
            m = hashlib.sha256()
            m.update(src.encode())
            h = m.hexdigest()
            _items.append({'src': h})
            _ = join(dn, h + '.' + src.split('.')[-1])
            if isfile(_):
                i += 1
                if not args.hide:
                    print('Skip {}'.format(_))
                continue
            if not args.hide:
                print('Downloading photo # {}/{} ({})'.format((i+offset), count, src,))

            threads.addThread(_safe_downloader, (src, _))

            i += 1
            if i % 50 == 0:
                threads.startAll()
        threads.startAll()

        with open('{}/_{}'.format(dn, offset), 'w') as it:
            it.write(json.dumps(_items))

        if len(items) > 999:
            self.downloadPhotos(album, (offset + len(items)))

    def photosGetAlbums(self, owner_id: str = 0):
        data = request('photos.getAlbums', 'owner_id=' + owner_id)
        self.albums = json.loads(data)
        return data

    def photos(self):
        if not (isinstance(self.albums, object) and 'response' in self.albums and 'items' in self.albums.get('response')):
            return False
        url = ','.join(map(lambda a: str(a.get('id'))+':6000', self.albums.get('response').get('items')))
        print(url)
        exit()
        data = request('execute.getAllUserPhotos', '')
        return data

    def _movePhotos(self, to, items):
        def _(_ids):
            if not len(_ids):
                return None
            return request('execute.photosMove', 'photos={}&to={}&owner_id={}'.format(','.join(_ids), to, user))

        ids = []
        for i, j in enumerate(items):
            if i and i % 25 == 0:
                sleep(2)
                _(ids)
                print('sleep 2sec. loop %d' % i)
                ids = []
            if j:
                ids.append('%d' % j)
        sleep(2)
        _(ids)

    def _deletePhotos(self, items):
        def _(_ids):
            if not len(_ids):
                return None
            return request('execute.deletePhotos', 'photos={}&owner={}'.format(','.join(_ids), user))

        ids = []
        for i, j in enumerate(items):
            if i and i % 25 == 0:
                sleep(2)
                _(ids)
                print('sleep 2sec. loop %d' % i)
                ids = []
            ids.append('%d' % j)
        sleep(3)
        _(ids)

    def _copyPhotos(self, items, owner):
        from captcha_decoder import decoder

        def _(_ids):
            if not len(_ids):
                return []
            return request('execute.photosCopy', 'photos={}&owner_id={}'.format(','.join(_ids), owner))

        _items = []
        ids = []
        print('Count items: %d' % len(items))
        _captcha_img = '/tmp/__vk_captcha_img.png'

        for i, j in enumerate(items):
            if i and i % 25 == 0:
                print('Sleeping 10 sec')
                sleep(10)
                __ = json.loads(_(ids))
                error = __.get('error', '')
                _ERR = __.get('execute_errors', [{}])[0].get('error_msg', '')
                if _ERR:
                    print(_ERR)
                    # exit()
                if error:
                    # __ = json.loads(_(ids))
                    print(error['error_msg'])
                    if error.get('error_code') == 14:

                        __n = 0
                        while True:
                            print('try solving')

                            captcha_sid = error.get('captcha_sid')
                            captcha_img = error.get('captcha_img')

                            _safe_downloader(captcha_img, _captcha_img)

                            solved = decoder(_captcha_img)

                            print(solved)

                            if __n > 10 or not len(solved):
                                solved = input('\nNot solved. Need manual!\nSee {}\n'.format(_captcha_img))

                            __ = json.loads(request('execute.photosCopy', 'photos={}&owner_id={}&captcha_sid={}&captcha_key={}'.format(
                                ','.join(ids),
                                owner,
                                captcha_sid,
                                solved
                            )))
                            __n += 1

                            if not __.get('error'):
                                break

                            sleep(1)


                    sleep(1)
                _items += __.get('response', [])
                print('sleep 2sec. loop %d' % i)
                ids = []
            ids.append('%d' % j)
        sleep(2)
        __ = json.loads(_(ids))
        error = __.get('error', '')
        if error:
            print(error)
        _items += __.get('response', [])
        # print(_items)
        # exit()
        return _items

    def movePhotos(self, ids=None):
        to = '249795469'
        data = json.loads(request('execute.getAllUserPhotos', 'user={}&albums=saved:6000'.format(user)))

        if data:
            self._movePhotos(to, data['response'])

    def uploadPhotos(self):
        if uploadAlbumId == '':
            print('upload_album_id is empty')
            return False

        # if need delete old uploaded photos
        # delete album here

        data = json.loads(request('photos.getUploadServer', 'album_id=' + str(uploadAlbumId)))
        if not data.get('response', False) or not data.get('response').get('upload_url', False):
            return False
        url = data.get('response').get('upload_url')
        path = join(getcwd(), 'vk_upload_files')
        if not isdir(path):
            return False
        uploadedPath = join(path, 'uploaded')
        if not isdir(uploadedPath):
            makedirs(uploadedPath, 0o777, True)
        _files = [f for f in listdir(path) if isfile(join(path, f))]
        files = []
        for f in _files:
            _, ext = splitext(f)
            if ext in ['.jpeg', '.jpg', '.png']:
                files.append(f)
        i = 0
        n = 0
        countFiles = len(files)
        _list = []
        _move = []
        if countFiles > 0:
            if not args.hide:
                print('uploading start')
            for f in files:
                if i == 5:
                    n += 5
                    self._upload(url, _list)
                    sleep(1) # на всякий случай
                    for _ in _move:
                        _[1].close()
                        rename(_[0], join(uploadedPath, basename(_[0])))
                    print('uploaded ' + str(n) + '/' + str(countFiles))
                    i = 0
                    _list = []
                    _move = []
                index = 'file' + str(i+1)
                fileName = join(path, f)
                d = open(fileName, 'rb')
                _list.append((index, ('image.png', d,)))
                _move.append((fileName, d,))
                i += 1
            if i != 5:
                self._upload(url, _list)
                for _ in _move:
                    _[1].close()
                    rename(_[0], join(uploadedPath, basename(_[0])))
            if not args.hide:
                print('uploaded finish')

    def summary(self):
        print(json.loads(request('execute.getSummaryData', '')))

    def copyPhotos(self):
        to = '249798346'
        album_id = 'wall'
        owner = '-127518015'
        items = json.loads(request('execute.photosGetIds', 'owner=%s&album=%s' % (owner, album_id))).get('response', [])

        # items = items[0:2]
        moved_photos = self._copyPhotos(items, owner)
        print(len(moved_photos))
        exit()

        if len(items):
            self._movePhotos(to, moved_photos)

    def deleteSavedPhotos(self):
        items = json.loads(request('execute.photosGetIds', 'owner=%s&album=%s' % (user, 'saved'))).get('response', [])
        self._deletePhotos(items)


newUser = User()
# newUser.photosGetAlbums()
# newUser.photos()
# newUser.uploadPhotos()
# newUser.downloadPhotos(input("Paste album number\n"))
# exit()

if args.m:
    method = args.m
else:
    method = input("Method: \n")
# moreParams = input("More params: \n")
if method == '-1':
    newUser.downloadPhotos(input("Paste album number\n"))
if method == '-2':
    owner_id = input("Paste owner id\n")
    newUser.photosGetAlbums(owner_id)
    for i in newUser.albums['response']['items']:
        print(owner_id + '_' + str(i['id']))
if method == '-3':
    newUser.movePhotos()
if method == '-4':
    newUser.copyPhotos()
if method == '-5':
    newUser.summary()
if method == '-6':
    newUser.deleteSavedPhotos()

exit()

m = getattr(newUser, method)
print(json.dumps(json.loads(m()), sort_keys=True, indent=4))
