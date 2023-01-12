# This is a crawler for pixiv with asyncio and httpx  
The `api` urls used in this program are copied from another pixiv crawler [PixivCrawler](https://github.com/CWHer/PixivCrawler/blob/master/pixiv_crawler/crawlers/bookmark_crawler.py) due to my Safari seems not to be able to get the ajax url.

# implement
This program could be divided into these functions:

`Queue` and `handler`  

As to `Queue`, four queues were used in order to send
- `artworks' id` to `httpx`
- `image_url` to `httpx`
-  `image_content` to `Saver`(which is for storaging the images)
-  `log` to `Log`. 
-  and so on

Apart from these, after all the works were done, the `ShutDown` signal would be sent.

The massage from handler to handler ususally contain its contents' type(such as url, content, error, etc.).

It can also avoid downloading images existing by `TaskManager`.
 
 # tips

It's not always succeed in one time. Due to http2, there would always be some errors that lead to fail, so try again until the `log.txt` becoming empty.

# New feature

## 2022.1.13
- Fixed the bug caused by simply check the `path.exits` to judge if all the pictures downloaded. Due to the case that one pixiv id may diredct to multiple pictures, simply check the id existence always can not work perfectly. In additon, shuting done the corotines through `Log` is not good, so add the `TaskManager`. 
- `show_details_enable` and `http2_enable` options is added.
- In `Crawler`, errors are dealt with `error handler`.