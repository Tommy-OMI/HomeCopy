# HomeCopy 系统设计

## 1. 项目目标

HomeCopy 是一个运行在多台 Windows / macOS 电脑上的短文本传输工具。

核心目标：

- 每台电脑运行一个桌面客户端
- 用户可以手动选择目标机器发送短文本
- 接收端自动将收到的文本写入系统剪贴板
- 中转服务部署在家里一台长期在线的电脑上
- 第一版只支持短文本，不支持文件和图片

## 2. 使用场景

典型场景：

- 在 Mac 上复制一段命令，发到 Windows 电脑直接粘贴
- 在办公室电脑和家里电脑之间传送验证码、链接、代码片段
- 在多台设备间快速传输临时文本，而不是打开聊天工具或网盘

## 3. 总体架构

系统由两部分组成：

1. 中转服务 `relay-server`
2. 桌面客户端 `desktop-client`

工作方式：

1. 每台客户端启动后连接中转服务
2. 客户端使用设备 ID 和共享 token 完成注册
3. 服务端维护在线设备列表
4. 用户在客户端输入文本并选择目标设备
5. 服务端将消息转发给目标设备
6. 目标设备收到消息后自动写入本机剪贴板

架构示意：

```text
[Mac Client] ----\
                  \
                   >---- [Relay Server @ Home PC] ---- [日志]
                  /
[Windows Client]-/
```

## 4. 技术选型

### 4.1 服务端

- Python 3.11+
- FastAPI
- Uvicorn
- WebSocket
- Pydantic

推荐原因：

- 适合快速构建长连接服务
- 协议定义清晰
- 后续扩展 HTTP 管理接口也方便

### 4.2 客户端

- Python 3.11+
- PySide6
- websockets
- pyperclip
- plyer 或平台原生通知封装

推荐原因：

- PySide6 可以做稳定的跨平台桌面 UI
- Python 代码可复用协议模型和配置逻辑
- 打包到 Windows 和 macOS 都比较顺

### 4.3 部署与网络

推荐方案：

- 家里一台电脑部署服务端
- 所有电脑安装 Tailscale
- 客户端通过 Tailscale 内网地址连接服务端

这样可以避免：

- 公网端口暴露
- DDNS
- 证书和反向代理的初期复杂度

## 5. 功能范围

### 5.1 MVP 功能

- 设备注册
- 在线设备列表
- 手动选择目标设备
- 发送短文本
- 自动写入接收端剪贴板
- 消息到达通知
- 自动重连
- 本地最近消息记录

### 5.2 第一版不做

- 文件传输
- 图片传输
- 离线消息
- 多账号系统
- 云端历史同步
- 端到端加密

## 6. 设备与身份设计

每台设备需要配置以下信息：

- `device_id`：唯一设备标识，例如 `macbook-air-home`
- `device_name`：显示名称，例如 `MacBook Air Home`
- `auth_token`：共享密钥
- `server_url`：服务端 WebSocket 地址

约束：

- `device_id` 只允许字母、数字、短横线
- `device_id` 在整个系统中必须唯一
- 同名设备重复登录时，新连接顶掉旧连接

## 7. 通信协议设计

通信协议使用 JSON 文本消息，全部通过 WebSocket 传输。

### 7.1 注册消息

客户端发送：

```json
{
  "type": "register",
  "protocol_version": 1,
  "device_id": "macbook-air-home",
  "device_name": "MacBook Air Home",
  "token": "shared-secret"
}
```

服务端返回：

```json
{
  "type": "register_ok",
  "self": "macbook-air-home",
  "online_devices": [
    {
      "device_id": "win-office",
      "device_name": "Office Windows"
    }
  ]
}
```

### 7.2 发送文本

客户端发送：

```json
{
  "type": "send_text",
  "request_id": "9f0f7c8d-6ad8-43ba-a4fb-763e7f0a4b74",
  "to": "win-office",
  "text": "这是一段需要发送的短文本"
}
```

### 7.3 投递文本

服务端发送给目标客户端：

```json
{
  "type": "incoming_text",
  "message_id": "c3a9d2c3-1fdb-48a1-8bb0-8a7f04d8a6df",
  "from": "macbook-air-home",
  "from_name": "MacBook Air Home",
  "text": "这是一段需要发送的短文本",
  "sent_at": "2026-04-29T21:30:00Z"
}
```

### 7.4 发送确认

服务端回给发送端：

```json
{
  "type": "send_ack",
  "request_id": "9f0f7c8d-6ad8-43ba-a4fb-763e7f0a4b74",
  "status": "ok"
}
```

### 7.5 在线设备列表更新

```json
{
  "type": "device_list",
  "devices": [
    {
      "device_id": "macbook-air-home",
      "device_name": "MacBook Air Home"
    },
    {
      "device_id": "win-office",
      "device_name": "Office Windows"
    }
  ]
}
```

### 7.6 错误消息

```json
{
  "type": "error",
  "code": "DEVICE_OFFLINE",
  "message": "Target device is offline"
}
```

建议错误码：

- `AUTH_FAILED`
- `INVALID_MESSAGE`
- `DEVICE_OFFLINE`
- `TEXT_TOO_LONG`
- `INTERNAL_ERROR`

## 8. 服务端设计

### 8.1 职责

服务端只负责：

- 认证
- 设备注册
- 维护在线连接
- 消息转发
- 广播设备列表
- 事件日志

服务端不负责：

- 持久化聊天历史
- 富文本处理
- 剪贴板逻辑

### 8.2 内部模块划分

建议目录：

```text
server/
  app.py
  connection_manager.py
  protocol.py
  auth.py
  config.py
  logging_setup.py
```

各模块职责：

- `app.py`：FastAPI 启动入口和 WebSocket 路由
- `connection_manager.py`：维护 `device_id -> websocket`
- `protocol.py`：消息模型校验与转换
- `auth.py`：token 校验
- `config.py`：环境变量读取
- `logging_setup.py`：日志初始化

### 8.3 连接管理策略

服务端维护一个内存映射：

```text
device_id -> {
  websocket,
  device_name,
  connected_at,
  remote_addr
}
```

策略：

- 新设备注册成功后写入映射
- 若同名设备已在线，则断开旧连接并保留新连接
- 连接关闭时移除映射
- 每次在线状态变化后广播最新设备列表

### 8.4 消息处理流程

1. 客户端连接到 `/ws`
2. 首条消息必须是 `register`
3. 校验 token 和消息结构
4. 注册设备并广播设备列表
5. 持续接收客户端消息
6. 收到 `send_text` 后校验长度、目标和格式
7. 转发给目标设备
8. 回送 `send_ack` 或 `error`

## 9. 客户端设计

### 9.1 职责

客户端负责：

- 管理与服务端的连接
- 展示在线设备
- 发送文本
- 接收文本
- 自动写入系统剪贴板
- 弹出通知
- 显示本地最近记录

### 9.2 界面设计

主界面建议包含以下区域：

- 顶部状态栏：连接状态、本机名称、服务端地址
- 左侧设备列表：显示在线设备
- 右侧输入区：输入要发送的文本
- 操作按钮：发送、清空、刷新
- 底部记录区：最近接收和发送记录

推荐交互：

- 启动后自动连接
- 连接成功后自动刷新设备列表
- 双击设备可快速选中为目标设备
- 输入框支持多行文本
- 成功发送后清空输入框

### 9.3 剪贴板处理

接收到 `incoming_text` 后：

1. 校验文本长度
2. 调用剪贴板服务写入文本
3. 写入成功后显示桌面通知
4. 在本地历史中追加一条记录

注意事项：

- 只写纯文本
- 不执行命令
- 不自动打开链接

### 9.4 自动重连

客户端断线后应自动重连，建议指数退避：

- 第 1 次：1 秒
- 第 2 次：2 秒
- 第 3 次：5 秒
- 第 4 次及以后：10 秒

重连成功后自动重新注册设备。

## 10. 配置设计

### 10.1 服务端配置

`.env` 示例：

```env
HOST=0.0.0.0
PORT=8765
AUTH_TOKEN=replace-with-a-long-random-secret
LOG_LEVEL=INFO
MAX_TEXT_LENGTH=20000
```

### 10.2 客户端配置

`config.json` 示例：

```json
{
  "device_id": "win-office",
  "device_name": "Office Windows",
  "server_url": "ws://100.101.102.103:8765/ws",
  "auth_token": "replace-with-a-long-random-secret",
  "auto_copy_on_receive": true,
  "show_notification": true,
  "history_limit": 50
}
```

## 11. 安全设计

### 11.1 第一版最低安全要求

- 所有客户端必须提供正确 token 才能注册
- 限制最大文本长度，默认 `20000`
- 服务端只接受 JSON 文本消息
- 服务端不执行任何客户端内容
- 日志中不记录完整敏感文本，可只记录来源、目标和长度

### 11.2 推荐网络安全方案

如果走 Tailscale：

- 服务端仅通过 Tailscale 地址访问
- 不对公网开放端口
- 降低暴露面

如果未来改为公网：

- 必须切换到 `wss://`
- 加反向代理和证书
- 加入 IP 限制或额外认证

### 11.3 后续可增强项

- 每设备独立密钥
- 设备授权名单
- 消息签名
- 端到端加密

## 12. 异常与边界行为

明确以下行为：

- 目标设备离线：发送失败并提示
- 文本超长：本地先拦截，不发出
- 服务端断开：客户端进入重连状态
- 服务端重启：客户端应自动恢复
- 剪贴板写入失败：保留消息并提示失败
- 同名设备重复上线：新连接顶掉旧连接

## 13. 日志与可观测性

### 13.1 服务端日志

记录：

- 设备上线和下线
- 认证成功和失败
- 消息转发成功和失败
- 未处理异常

建议日志字段：

- 时间
- 级别
- 设备 ID
- 目标设备 ID
- 文本长度
- 错误码

### 13.2 客户端日志

记录：

- 连接成功和断开
- 自动重连次数
- 发送和接收事件
- 剪贴板写入结果

## 14. 部署设计

### 14.1 服务端部署

部署位置：家里长期在线的电脑

要求：

- Python 3.11+
- Tailscale 已安装并在线
- 稳定电源和网络

启动方式：

```bash
uvicorn app:app --host 0.0.0.0 --port 8765
```

后续可选常驻方式：

- macOS `launchd`
- Windows 服务
- Docker

### 14.2 客户端部署

每台客户端电脑：

- 安装客户端程序
- 配置 `device_id`
- 配置服务端地址
- 配置共享 token

打包建议：

- Windows：PyInstaller 打成 `.exe`
- macOS：PyInstaller 打成 `.app`

## 15. 目录结构建议

```text
homecopy/
  server/
    app.py
    connection_manager.py
    protocol.py
    auth.py
    config.py
    logging_setup.py
  client/
    main.py
    config.py
    network/
      client.py
    ui/
      main_window.py
    services/
      clipboard_service.py
      notification_service.py
      history_service.py
  shared/
    models.py
    constants.py
  requirements.txt
  README.md
```

## 16. 开发顺序建议

建议按下面顺序推进：

1. 先做服务端 WebSocket 注册和转发
2. 写一个命令行客户端验证协议
3. 做桌面客户端 UI
4. 加入剪贴板写入和通知
5. 加入打包、日志和自动重连

原因：

- 先把协议跑通，排错成本最低
- UI 放后面做，不会拖慢核心验证
- 打包放最后，避免开发期反复折腾

## 17. MVP 验收标准

满足以下条件即可视为第一版可用：

- 至少两台不同系统电脑可同时在线
- A 设备向 B 设备发送文本成功
- B 设备在 1 秒内写入系统剪贴板
- 在线列表能随上下线变化而更新
- 服务端重启后客户端能自动恢复连接
- 断网后恢复网络，客户端无需重启即可继续使用

## 18. 后续演进方向

在 MVP 稳定后，可以考虑：

- 托盘常驻
- 快捷键快速呼出窗口
- 最近发送模板
- 历史搜索
- 文件发送
- 端到端加密
- 多用户隔离

## 19. 结论

这套方案适合你的实际使用方式：

- 设备数量不多
- 主要传的是短文本
- 希望跨 Windows 和 macOS
- 希望交互直观，接收后能直接粘贴

把中转服务放在家里电脑上是可行的；如果配合 Tailscale，会比直接做公网暴露更稳、更省心，也更适合第一版落地。
