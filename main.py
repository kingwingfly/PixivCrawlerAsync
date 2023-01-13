import httpx
import asyncio
import os

# from parsel import Selector
# import glob

user_id = 0
my_uid = 0
ids_url = f'https://www.pixiv.net/ajax/user/{user_id}/profile/all?lang=zh'
bookmak_url = (
    f'https://www.pixiv.net/ajax/user/{my_uid}/illusts' + '/bookmark/tags?lang=zh'
)
number_of_coroutines = 64
halt = 1
http2_enable = False
show_details_enanle = False
json_save_enable = False

cookie = ''
headers = {
    # 'Accept': 'image/webp,image/avif,video/*;q=0.8,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5',
    # 'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
    # 'Accept-Encoding': 'gzip, deflate, br',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Safari/605.1.15',
    # 'Host': 'www.pixiv.net',
    'Referer': 'https://www.pixiv.net/artworks/104147976',
    # 'Connection': 'keep-alive',
    'Cookie': cookie,
    # 'x-user-id': my_uid
}

if not os.path.exists(f'downloads/{user_id}'):
    os.mkdir(f'downloads/{user_id}')
if os.path.exists('log.txt'):
    os.remove('log.txt')

NO_DOWMLOAD_TASK = True


class Crawler(object):
    def __init__(self) -> None:
        self.headers = headers

    @staticmethod
    async def error_handler(type_, err='', target_url=''):
        await queue_log.put(str(err) + '\n' + target_url)
        if type_ == 'download':
            await queue_manager.put('fail')
        if type_ in ['ids', 'image_urls']:
            await queue_manager.put('ajax_fail')

    async def run(self):
        async with httpx.AsyncClient(http2=http2_enable) as client:
            while task := await queue_task.get():
                if task == "ShutDown":
                    return
                type_, target_url = task
                name = target_url.split('/')[-1]
                if show_details_enanle:
                    print(f'Rrequested {target_url}')
                try:
                    response = await client.get(
                        url=target_url,
                        headers=self.headers,
                        follow_redirects=True,
                        timeout=20,
                    )
                except Exception as e:
                    await self.error_handler(type_, e, target_url)
                    continue
                if response.status_code != 200:
                    print('Network Error!')
                    await self.error_handler(
                        type_, f'NetworkError {response.status_code}', target_url
                    )
                    continue
                if type_ in ['ids', 'image_urls']:
                    await queue_ajax_response.put((type_, response))
                elif type_ == 'download':
                    name = target_url.split('/')[-1]
                    await queue_image_data.put((name, response.content))
                await asyncio.sleep(halt)


class ResponseParser(object):
    def __init__(self) -> None:
        ...

    async def id_parse(self, response):
        ids = response.json()['body']['illusts'].keys()
        if json_save_enable:
            import json
            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(response.json(), f, ensure_ascii=False)
        for id in list(ids):
            image_info_url = f'https://www.pixiv.net/ajax/illust/{id}/pages?lang=zh'
            await queue_task.put(('image_urls', image_info_url))
            await queue_manager.put('ajax_add')

    async def image_url_parse(self, response):
        # 可能存在多张图片
        image_urls = [
            image_info['urls']['original'] for image_info in response.json()['body']
        ]
        for image_url in image_urls:
            name = image_url.split('/')[-1]
            if os.path.exists(f'downloads/{user_id}/{name}'):
                continue
            await queue_manager.put('add')
            await queue_task.put(('download', image_url))
            NO_DOWMLOAD_TASK = False
        await queue_manager.put('ajax_finish')

    async def parser_run(self):
        while data := await queue_ajax_response.get():
            if data == "ShutDown":
                return
            type_, response = data
            parse_methods = {
                'ids': self.id_parse,
                'image_urls': self.image_url_parse,
            }
            await parse_methods[type_](response)


class ImageSaver(object):
    def __init__(self) -> None:
        ...

    async def saver_run(self):
        while content := await queue_image_data.get():
            if content == "ShutDown":
                return
            name, content = content
            with open(f'downloads/{str(user_id)}/{name}', 'wb') as f:
                f.write(content)
                if show_details_enanle:
                    print(f"saved {name}")
            await queue_manager.put('finish')


class Log(object):
    def __init__(self) -> None:
        ...

    async def log_run(self):
        while msg := await queue_log.get():
            if msg == "ShutDown":
                return
            with open('log.txt', 'a', encoding='utf-8') as f:
                f.write(f'{msg}\n')
        print("All Finish")


class TasksManager(object):
    def __init__(self) -> None:
        self.total = 0
        self.finished = 0
        self.faild = 0
        self.ajax_waiting = 0
        self.loaded = False

    @staticmethod
    async def shutdown():
        print('Shutting down')
        for queue in [queue_ajax_response, queue_image_data, queue_log, queue_manager]:
            await queue.put("ShutDown")
        for _ in range(number_of_coroutines):
            await queue_task.put("ShutDown")

    async def add(self):
        self.total += 1
        await self.check(terminate=False)

    async def finish(self):
        self.finished += 1
        await self.check(terminate=True)

    async def fail(self):
        self.faild += 1
        await self.check(terminate=True)

    async def ajax_add(self):
        self.ajax_waiting += 1
        if show_details_enanle:
            print(f'ajax loaded?   {self.loaded}   {self.ajax_waiting}')
            print(f'Total tasks:   {self.total}')


    async def ajax_finish(self):
        self.ajax_waiting -= 1
        if show_details_enanle:
            print(f'ajax loaded?   {self.loaded}   {self.ajax_waiting}')
            print(f'Total tasks:   {self.total}')
        await self.ajax_check()

    async def check(self, terminate=False):
        print(
            f"{self.finished+self.faild}/{self.total} | Total: {self.total} | Finished: {self.finished} | Failed: {self.faild}"
        )
        if self.total == self.finished + self.faild and self.loaded and terminate:
            await self.shutdown()

    async def ajax_check(self):
        if self.ajax_waiting == 0:
            self.loaded = True
            if NO_DOWMLOAD_TASK:
                await self.check(terminate=True)
        else:
            self.loaded = False

    async def manager_run(self):
        while task := await queue_manager.get():
            if task == 'ShutDown':
                return
            methods = {
                'add': self.add,
                'finish': self.finish,
                'fail': self.fail,
                'ajax_add': self.ajax_add,
                'ajax_finish': self.ajax_finish,
                'ajax_fail': self.ajax_finish,
            }
            await methods[task]()
            


async def main():
    await queue_task.put(('ids', ids_url))
    user_page_crawlers: list[Crawler] = [Crawler() for _ in range(number_of_coroutines)]
    coros_userpage = [
        user_page_crawler.run() for user_page_crawler in user_page_crawlers
    ]

    parser = ResponseParser()
    coro_parser = [parser.parser_run()]

    image_saver = ImageSaver()
    coro_saver = [image_saver.saver_run()]

    log = Log()
    coro_log = [log.log_run()]

    manager = TasksManager()
    coro_manager = [manager.manager_run()]

    await asyncio.gather(
        *(coros_userpage + coro_parser + coro_saver + coro_log + coro_manager)
    )
    print("All Finished")


if __name__ == '__main__':
    queue_task = asyncio.Queue()
    queue_ajax_response = asyncio.Queue()
    queue_image_data = asyncio.Queue()
    queue_log = asyncio.Queue()
    queue_manager = asyncio.Queue()
    asyncio.run(main())
