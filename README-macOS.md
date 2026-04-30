# HomeCopy macOS Package

这个目录是单独整理出来给 macOS 打包用的。

包含内容：

- `homecopy/` 源码
- `requirements.txt`
- `.env.example`
- `package_macos.command`

## 一条命令打包 `.app`

首次在 Mac 上：

```bash
chmod +x *.command
./package_macos.command
```

脚本会自动在当前目录创建 `.venv-packaging/` 作为独立打包环境，
不会向系统 Python 安装依赖。

打包完成后，最终可分发目录在：

```text
dist/HomeCopyClient-macOS/
```

里面会包含：

- `HomeCopyClient.app`
- `.env.example`

如果需要修改内置 server 的端口或局域网发现参数，把 `.env.example` 复制为：

```text
~/Library/Application Support/HomeCopy/.env
```

## 说明

这个目录已经是独立可复制的 macOS 打包源目录。
真正的 `.app` 仍然需要在一台 macOS 机器上执行打包，不能在 Windows 上直接产出。
运行后的配置、日志和历史会写到 `~/Library/Application Support/HomeCopy/`，不会写进 `.app` 包里。
