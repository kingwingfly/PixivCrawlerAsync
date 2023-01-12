# 这是一个httpx实现的Pixiv的异步爬虫

所使用的 `api` 链接借鉴于此项目[PixivCrawler](https://github.com/CWHer/PixivCrawler/blob/master/pixiv_crawler/crawlers/bookmark_crawler.py)。

因为我的Safari无法从浏览器中找到请求的`ajax`链接

# 实现

这个程序主要有两个功能组成：

队列(`Queue`) 和 处理者(`handler`)

对于队列，主要是传递

- 插画id给httpx
- 图片链接给httpx
- 图片内容给储存器(Saver)
- 日志给日志处理(Log)
- 等等

此外，当所有任务完成后，`ShutDown`信息会发出，收到信息的`handler`会停止。

在`handler`之间传递的信息通常包括信息的类型，比如错误、目标链接、图片内容等等。

同时也能够避免重复下载已有图片，通过`TaskManager`实现的。

# 小提示

由于`http2` 的原因，往往无法一次便成功下载全部图片。所以请多运行几次，直到`log.txt`为空。

# 新特性
## 2022.1.13
- 修复了简单检查 `path.exits` 来判断图片是否已下载导致的遗漏图片的问题。因为存在多张图片共用一个pixiv id的情况，简单检查一张图片的id是否已经存在来判断是否下载往往不能有效工作. 此外, 通过 `Log` 来关闭所有协程并不合理，所以增加了`TaskManager`类.。
- 添加了 `show_details_enable` 和 `http2_enable` 可选项。
- 在 `Crawler`中, 错误处理集成到了 `error handler` 方法中。


