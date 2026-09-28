# 网页做题悬浮助手 Demo

Windows floating quiz assistant。

这是一个 Windows 10/11 桌面 Demo：选择已经打开的窗口，通过 Windows Graphics Capture 实时预览当前画面，再由你主动把某一帧发送给支持图片输入的大模型进行题目识别和解答。

当前版本只做题目识别和解答，不会自动操作、填写或提交网页。

## 安装

需要 Python 3.11 或更高版本。在项目目录打开 PowerShell，运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-demo.ps1
```

虚拟环境安装到 `D:\codex\venvs\quiz-assistant-demo`，pip 缓存和任务临时文件也位于 D 盘。安装脚本可以重复运行以更新代码。

## 启动和使用

1. 双击 `run-demo.cmd`。
2. 点击“刷新窗口”，选择要读取的浏览器或其他窗口。
3. 确认预览正常。
4. 填写服务商给出的 OpenAI 兼容 API 地址、API Key，以及支持图片输入的模型名。
5. 可填写“只给答案”“详细讲解”“重点看第 3 题”等补充说明。
6. 点击“识别并解答”，在结果框中复制答案。

勾选“置顶显示”可让助手保持在其他普通窗口上方。浏览器切换标签页后，预览会读取浏览器窗口当前显示的标签页。

## API 地址

- 可以填写服务商提供的 `.../v1` 地址，程序会追加 `/chat/completions`。
- 也可以直接填写完整的 `.../chat/completions` 地址。
- 模型必须支持 OpenAI 风格的 `image_url` 图片输入；纯文本模型会返回错误。
- Gemini 等服务只有在其端点兼容上述格式时才能使用；本 Demo 使用 API Key，不读取 Google 登录状态，也不实现 Google OAuth。

## 隐私

- 只有点击“识别并解答”时，当前冻结截图才会发送给你填写的 API。
- 实时预览只在本机内存中处理，不会自动发起模型请求。
- API Key 只保存在当前进程内存中，关闭程序后丢失。
- 截图不会自动保存到磁盘，日志也不会记录 Key 或图片数据。

## 已知限制

- 最小化或受 DRM/系统保护的窗口可能无法捕获；请恢复窗口后重试。
- 首版按整个顶层窗口捕获，不单独列出浏览器标签页。
- Demo 不会点击网页、填写答案或自动提交。
- “停止请求”会立即停止等待并忽略迟到结果；已经发出的网络请求可能仍会在后台结束。

## 测试

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& 'D:\codex\venvs\quiz-assistant-demo\Scripts\python.exe' -m pytest -q
```

## 文档维护

每次功能、安装方式或使用流程发生变化时，应在同一个更新中同步修改本 README，确保仓库首页说明与当前版本一致。
