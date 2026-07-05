# ZXtextAI 安装与启动指南

> 一款集 **AI 需求评审 / AI 测试用例生成 / AI 驱动浏览器自动化 / APP 自动化 / 接口自动化** 于一体的软件测试平台。
>
> 本文档介绍如何从零把项目跑起来（开发环境 + 生产部署）。

---

## 一、环境要求

| 组件 | 版本 | 说明 |
| --- | --- | --- |
| **Python** | 3.11 ~ 3.13 | 后端 Django 5.1 |
| **Node.js** | 18 LTS 及以上 | 前端 Vue3 + Vite6 |
| **MySQL** | 8.0+ | 主数据库，建议 InnoDB + utf8mb4 |
| **Redis** | 7.0+ | Channels、Celery、验证码、缓存 |
| **Google Chrome** | 最新稳定版 | UI 自动化 `browser-use` 依赖 |
| **操作系统** | Windows 10/11、macOS、Linux | 已在 Windows 11 上验证 |

可选：Docker 20.10+ 与 docker-compose v2（走容器化部署）。

---

## 二、快速开始（本地开发）

### 1. 克隆项目并进入根目录

```bash
git clone <你的仓库地址> ZXtextAI
cd ZXtextAI
```

### 2. 后端启动

```powershell
# 进入后端目录
cd backend

# 复制并按需修改环境变量
copy .env.example .env
# 打开 .env，至少配置：SECRET_KEY / DB_* / REDIS_URL

# 使用项目已带的 venv（推荐）
.\venv\Scripts\activate

# 或者重建虚拟环境
# python -m venv venv
# .\venv\Scripts\activate
# pip install -r requirements.txt

# 首次启动前：初始化数据库
# （请先在 MySQL 里建好 .env 中 DB_NAME 指定的空库，字符集 utf8mb4）
python manage.py migrate

# 创建管理员账号（可选，用于访问 /admin）
python manage.py createsuperuser

# 启动开发服务（默认 http://127.0.0.1:8000）
python start.py
```

### 3. 前端启动

新开一个终端窗口：

```powershell
cd frontend

# 首次安装依赖（首次或依赖变更时执行）
npm install

# 启动开发服务器（默认 http://127.0.0.1:3000）
npm run dev
```

访问 `http://localhost:3000` 即可进入登录页。

### 4. 生产构建

```powershell
cd frontend
npm run build
# 产物位于 frontend/dist，可直接交给 nginx 或后端 collectstatic 托管
```

---

## 三、需要额外安装的插件 / 二进制

> 以下是**必须** / 强烈建议安装的第三方组件，均已写入 [requirements.txt](file:///c:/Users/Administrator/Desktop/实习/实习/软测/项目/ZXtextAI/backend/requirements.txt)，但部分仍需要一次性执行安装命令。

### 3.1 Playwright 浏览器驱动（UI 自动化必装）

安装完 Python 依赖后必须再执行一次：

```powershell
# 在 backend/venv 激活状态下
playwright install chromium
# 需要完整支持时可：playwright install
```

### 3.2 easyocr / opencv 首次运行

首次调用 OCR 或图像识别会自动下载模型（约 100MB），如需离线，请预先运行：

```powershell
python -c "import easyocr; easyocr.Reader(['ch_sim','en'])"
```

### 3.3 pytesseract（可选，验证码识别增强）

```powershell
# 安装二进制（Windows 从 UB Mannheim 下载安装包，加入 PATH）
# https://github.com/UB-Mannheim/tesseract/wiki
```

### 3.4 Redis（Windows）

推荐使用 [Memurai](https://www.memurai.com/) 或 WSL 中的 redis-server，
或者直接使用官方镜像：`docker run -d -p 6379:6379 redis:7`。

---

## 四、Docker 一键部署（可选）

前端目录已提供 `docker-compose.yml` 与 `Dockerfile`，可用作参考：

```powershell
cd frontend
docker compose up -d
```

后端建议单独准备 Dockerfile（本项目暂未内置）。

---

## 五、常用管理命令

```powershell
# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 生成 API 文档（drf-spectacular）
python manage.py spectacular --file schema.yml

# 收集静态资源
python manage.py collectstatic --noinput

# Celery 异步任务（若用到）
celery -A backend worker -l info -P eventlet
celery -A backend beat -l info
```

---

## 六、目录结构速览

```
ZXtextAI/
├── backend/                # Django 后端
│   ├── apps/               # 各业务模块（需求分析、UI自动化、APP自动化 等）
│   ├── backend/            # Django 项目配置（settings.py / urls.py / asgi.py）
│   ├── database/init.sql   # 建库脚本
│   ├── media/              # 上传/生成文件
│   ├── rizhi/logs/         # 运行日志
│   ├── requirements.txt
│   ├── start.py            # 一键启动脚本（uvicorn + asgi）
│   └── manage.py
├── frontend/               # Vue3 前端
│   ├── src/                # 源码
│   ├── dist/               # 构建产物
│   ├── vite.config.js
│   ├── nginx.conf
│   └── package.json
├── README.md               # 本文档
└── PROJECT_INTRO.md        # 项目介绍与技术栈
```

---

## 七、常见问题（FAQ）

**Q1：启动后前端提示 `Network Error / CORS`？**

- 检查 [.env](file:///c:/Users/Administrator/Desktop/实习/实习/软测/项目/ZXtextAI/backend/.env) 中的 `CORS_ALLOWED_ORIGINS` 是否包含 `http://localhost:3000`。
- 前端 [vite.config.js](file:///c:/Users/Administrator/Desktop/实习/实习/软测/项目/ZXtextAI/frontend/vite.config.js) 中 `proxy.target` 需指向 `http://127.0.0.1:8000`。

**Q2：AI 调用报 `exceeded model token limit`？**

- 项目已在 [ai_base.py](file:///c:/Users/Administrator/Desktop/实习/实习/软测/项目/ZXtextAI/backend/apps/ui_automation/ai_base.py) 内置**上下文自动截断重试**逻辑。若仍失败，请前往 **配置中心 → AI 模型配置** 切换到大上下文模型（如 `moonshot-v1-32k`、`moonshot-v1-128k`）。

**Q3：`playwright.exe install` 网络超时？**

- 设置国内镜像：
  ```powershell
  $env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"
  playwright install chromium
  ```

**Q4：数据库首次迁移报字符集错？**

- 建库语句使用：
  ```sql
  CREATE DATABASE zxtest CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  ```

**Q5：需求评审「死循环」/ 一直报 500？**

- 已在本仓库修复：前端会在 400/404 或连续 5 次异常时自动停止轮询，后端对无效 `task_id` 返回 400 而非 500。
- 若仍出现，请清理浏览器缓存后重试。

---

## 八、生产环境须知

1. `.env` 中 `DEBUG=False`，`SECRET_KEY` 使用强密钥。
2. `ALLOWED_HOSTS` / `CORS_ALLOWED_ORIGINS` 指定具体域名。
3. MySQL 建议开启慢查询日志，Redis 建议开启 AOF。
4. 前端由 nginx 托管 `frontend/dist`，反向代理 `/api` 至 8000。
5. 后端通过 `daphne` 或 `uvicorn --workers` 部署（ASGI，支持 WebSocket）。
