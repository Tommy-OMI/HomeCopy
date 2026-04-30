# HomeCopy

HomeCopy 是一个面向 Windows 的短文本中转工具。当前仓库已经落地了 MVP 的核心链路：

- FastAPI WebSocket relay server
- 共享协议模型
- 可运行的图形客户端
- 自动重连、本地历史、剪贴板写入、桌面通知
- 局域网自动发现 server
- 系统托盘与全局快捷键呼出
- 统一启动模式：先找局域网 server，找不到则自动自举本机 server

## 目录结构

```text
homecopy/
  server/
  client/
  shared/
scripts/
requirements.txt
.env.example
client_config.example.json
install_all.bat
start_server.bat
start_client.bat
stop_server.bat
stop_all.bat
build_client.bat
```

## 一键安装

```bash
install_all.bat
```

等价命令：

```bash
python scripts/install_all.py
```

## 一键启动

只启动中转服务：

```bash
start_server.bat
```

等价命令：

```bash
python scripts/start_server.py
```

一键停止：

```bash
stop_server.bat
stop_all.bat
```

## 服务端配置

1. 复制 `.env.example` 为 `.env`
2. 按需要修改 `AUTH_TOKEN`
3. 运行 `start_server.bat`

健康检查：

```bash
curl http://127.0.0.1:8765/healthz
```

局域网发现：

- server 启动后会通过 UDP `8766` 广播自己的 WebSocket 地址
- client 首次启动可以在配置弹窗里点 `Auto Discover Server`
- 统一版客户端启动时也会先等待几秒做自动发现
- 如果几秒内没有发现任何 server，会在本机后台启动内置 server，并把日志写到 `logs/server.log`
- 如果你的网卡较多或广播地址判断不准，可以在 `.env` 里手动设置 `DISCOVERY_ADVERTISE_HOST`
- `Device Name` 指的是每一台客户端设备，不是 server；`Device ID` 会由客户端自动生成
- 如果你家里设备自己用，可以把 `.env` 里的 `AUTH_TOKEN` 留空，客户端也不需要填写 token

## 启动客户端

直接启动即可：

```bash
start_client.bat
```

如果首次双击 `start_client.bat` 时还没有客户端配置，脚本会自动生成 `configs/clients/client.local.json`，并在进入主界面前弹出首次启动配置窗口。这个弹窗支持局域网自动发现 server 地址；如果几秒内没发现局域网 server，客户端会自动在本机后台拉起内置 server。

当前图形界面包含：

- 在线设备列表
- 多行文本输入
- 发送、清空、刷新
- 最小化到系统托盘
- 全局快捷键呼出窗口，可修改
- 本地历史记录
- 接收后自动写剪贴板
- 连接状态展示

## 当前已完成

- 设备注册与鉴权
- 在线设备列表广播
- 文本发送 / 投递 / 确认
- 目标设备自动写入剪贴板
- 简单桌面通知
- 自动重连与本地历史
- PySide6 桌面窗口 MVP

## 打包客户端

Windows 下可以直接生成可复制运行的 GUI 可执行文件：

```bash
build_client.bat
```

产物输出到：

```text
dist/HomeCopyClient/
```

把整个 `HomeCopyClient` 目录复制到另一台 Windows 电脑即可运行。
打包完成后，脚本还会自动覆盖复制一份到：

```text
D:\HomeCopyClient
```

## 下一步建议

- 优化连接状态提示和错误引导
- 增加基础集成测试
