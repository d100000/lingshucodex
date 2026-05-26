# Ubuntu 一键部署

服务器环境: Ubuntu/Debian + systemd。

从开源社区下载项目后,进入项目根目录执行:

```bash
bash scripts/deploy-ubuntu.sh
```

脚本会完成:

- 安装 Python、Node.js、Nginx 等依赖。
- 将项目部署到 `/opt/lingshu-codex`。
- 创建专用系统用户 `lingshu`。
- 生成 `backend/.env`,其中包含随机 `JWT_SECRET`。
- 初始化 SQLite 数据库: `/opt/lingshu-codex/backend/data/lingshu.db`。
- 构建前端静态文件。
- 创建并启动 systemd 服务 `lingshu-codex`。
- 配置 Nginx,托管前端并反代 `/api` 和 `/ws`。
- 可选配置 HTTPS。

部署完成后访问:

```text
http://你的域名或服务器IP/
http://你的域名或服务器IP/#/admin-console/login
```

首次进入管理后台时,页面会要求创建管理员账号和密码。项目不会内置默认管理账号。

常用命令:

```bash
sudo systemctl status lingshu-codex
sudo journalctl -u lingshu-codex -f
sudo nginx -t && sudo systemctl reload nginx
```

再次部署或升级时可以重复执行同一个脚本。脚本会保留:

- `/opt/lingshu-codex/backend/.env`
- `/opt/lingshu-codex/backend/data/`

也就是不会覆盖生产配置和 SQLite 数据库。
