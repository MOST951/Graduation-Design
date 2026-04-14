# 微博舆情情感分析系统 — Ubuntu 部署指南

> **适配环境:** Ubuntu 20.04 LTS / Docker Compose v2.35+ / 1Panel  
> **硬件要求:** 4GB 内存 / 2 核 CPU / 20GB 磁盘  
> **目录约定:** 下文统一以 `/root/weibo-analysis` 为项目根目录示例

---

## 一、一键部署步骤

### 1. 上传项目到虚拟机

```bash
# 方式一: SCP 上传 (从 Windows 本机)
scp -r ./weibo-sentiment-analysis root@<VM_IP>:/root/weibo-analysis

# 方式二: Git 克隆
cd /root && git clone <仓库地址> weibo-analysis
```

### 2. 安装 Docker (如已有 1Panel 可跳过)

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | bash

# 开机自启
sudo systemctl enable docker && sudo systemctl start docker

# 将当前用户加入 docker 组 (非 root 用户需要)
sudo usermod -aG docker $USER && newgrp docker

# 验证
docker --version
docker compose version
```

### 3. 配置环境变量

```bash
cd /root/weibo-analysis/deployment

# 从模板复制
cp .env.docker.example .env.docker

# 编辑配置
nano .env.docker
```

**开发测试默认值（已可直接启动）：**

| 变量 | 默认值 |
|------|--------|
| `DB_USER` | `weibo_user` |
| `DB_PASSWORD` | `123456` |
| `DB_ROOT_PASSWORD` | `123456` |
| `REDIS_PASSWORD` | `123456` |

**生产环境必须修改的配置项：**

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `DB_PASSWORD` | 数据库密码 | `MyStr0ng!Pass` |
| `DB_ROOT_PASSWORD` | Root 密码 | `R00t!Str0ng` |
| `REDIS_PASSWORD` | Redis 密码 | `R3dis!Strong` |
| `SECRET_KEY` | Flask 密钥 | 运行 `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_SECRET` | JWT 密钥 | 同上方法生成 |

> 注意：`.env` 中密码值不要加引号；仅当值包含空格或特殊字符时，使用单引号包裹。

### 4. 修复文件权限

```bash
cd /root/weibo-analysis

# 确保脚本可执行
chmod +x docker-cluster.sh
chmod +x deployment/scripts/*.sh

# 如果从 Windows 传来，修复换行符
sudo apt-get install -y dos2unix
find . -name "*.sh" -exec dos2unix {} \;
find . -name "*.yml" -exec dos2unix {} \;
find . -name "*.conf" -exec dos2unix {} \;
find . -name ".env*" -exec dos2unix {} \;
```

### 5. 一键启动

```bash
cd /root/weibo-analysis

# 首次部署 (自动构建镜像 + 启动所有服务)
./docker-cluster.sh

# 等价的一键 Compose 命令（显式 --env-file + 全 profile）
docker compose -f deployment/docker-compose.yml \
  --env-file deployment/.env.docker \
  --profile with-frontend \
  --profile with-java-backend \
  --profile with-spark \
  --profile with-bigdata up -d

# 查看状态
./docker-cluster.sh status

# 健康检查
./docker-cluster.sh health

# 一键验证 (MySQL/Redis/HBase/前后端)
bash deployment/scripts/health-check.sh
```

### 6. 验证访问

假设虚拟机 IP 为 `192.168.1.100`：

| 服务 | 地址 |
|------|------|
| 前端页面 | http://192.168.1.100:3001 |
| Flask API | http://192.168.1.100:5000/api/health |
| Java Backend | http://192.168.1.100:8081/api/actuator/health |
| Spark Web UI | http://192.168.1.100:8080 |

---

## 二、日常管理命令

```bash
# 启动集群 (保留数据)
./docker-cluster.sh start

# 停止集群 (保留数据)
./docker-cluster.sh stop

# 重启集群
./docker-cluster.sh restart

# 查看实时日志
./docker-cluster.sh logs

# 服务健康检查
./docker-cluster.sh health

# 销毁容器 (数据卷保留)
./docker-cluster.sh down

# 查看容器状态
./docker-cluster.sh status

# 运行部署自检
bash deployment/scripts/health-check.sh
```

---

## 三、1Panel 兼容说明

本项目使用 Docker Compose 标准 API，完全兼容 1Panel 的 Docker 管理：

- **容器名称前缀:** 所有容器以 `weibo_sentiment_` 开头，在 1Panel 容器列表中易于识别
- **网络:** 使用独立的 `weibo-net` 桥接网络，不与 1Panel 其他应用冲突
- **数据卷:** 使用命名卷 (named volumes)，1Panel 存储卷管理中可见
- **端口:** 默认端口可在 `.env.docker` 中修改，避免与 1Panel 已有服务冲突
- **不冲突:** 脚本仅管理 `weibo_sentiment_*` 容器，不影响 1Panel 管理的其他容器

---

## 四、数据持久化

| 数据 | 存储方式 | 说明 |
|------|----------|------|
| MySQL | `weibo_sentiment_mysql_data` 卷 | 所有数据库数据 |
| Redis | `weibo_sentiment_redis_data` 卷 | 缓存数据 (AOF 持久化) |
| 应用日志 | `weibo_sentiment_app_logs` 卷 | Flask 后端日志 |
| 模型缓存 | `weibo_sentiment_model_cache` 卷 | NLP 模型文件 |
| 集群日志 | `./logs/cluster-*.log` | 启停脚本操作日志 |

**数据安全：**
- `./docker-cluster.sh stop` / `start` 不会丢失任何数据
- `./docker-cluster.sh down` 只销毁容器，数据卷保留
- 彻底清理数据: `docker volume rm weibo_sentiment_mysql_data weibo_sentiment_redis_data`

---

## 五、常见问题排错指南

### 问题 1: 端口冲突

**现象:** `Error starting userland proxy: listen tcp4 0.0.0.0:3306: bind: address already in use`

**解决:**
```bash
# 查看谁在用这个端口
ss -tlnp | grep :3306

# 方案 A: 停止占用的服务
sudo systemctl stop mysql

# 方案 B: 修改 .env.docker 中的端口
# DB_PORT=3307
```

### 问题 2: Docker 权限不足

**现象:** `permission denied while trying to connect to the Docker daemon socket`

**解决:**
```bash
sudo usermod -aG docker $USER
newgrp docker
# 或重新 SSH 登录
```

### 问题 3: 容器启动失败 (Exit Code 非 0)

**排查步骤:**
```bash
# 查看容器日志
docker logs weibo_sentiment_web --tail=50
docker logs weibo_sentiment_db --tail=50

# 查看容器退出原因
docker inspect weibo_sentiment_web --format='{{.State.ExitCode}} {{.State.Error}}'

# 进入容器排查
docker exec -it weibo_sentiment_web bash
```

### 问题 4: MySQL 初始化失败

**现象:** Web 服务报 `Access denied` 或数据库连接失败

**解决:**
```bash
# 方案: 重建数据库 (会丢失数据!)
docker compose -f deployment/docker-compose.yml down
docker volume rm weibo_sentiment_mysql_data
./docker-cluster.sh start
```

### 问题 4.1: MySQL Access denied (密码已改但仍报错)

**原因:** 旧数据卷保留了历史账号/密码

**解决:**
```bash
# 会清空 MySQL 历史数据（仅开发测试环境建议）
docker compose -f deployment/docker-compose.yml down
docker volume rm weibo_sentiment_mysql_data
./docker-cluster.sh start
```

### 问题 4.2: Redis 连接超时或 NOAUTH

**解决:**
```bash
# 1) 确认 .env.docker 中 REDIS_PASSWORD 与应用配置一致
grep '^REDIS_PASSWORD=' deployment/.env.docker

# 2) 验证 Redis 密码
docker exec weibo_sentiment_redis redis-cli -a "$(grep '^REDIS_PASSWORD=' deployment/.env.docker | cut -d= -f2)" ping

# 3) 若仍异常，重建 Redis 卷（会清空缓存）
docker compose -f deployment/docker-compose.yml down
docker volume rm weibo_sentiment_redis_data
./docker-cluster.sh start
```

### 问题 4.3: HBase 无法连接 ZooKeeper

**解决:**
```bash
# 检查 ZooKeeper 是否健康
docker inspect --format='{{.State.Health.Status}}' weibo_sentiment_zookeeper

# 检查 HBase Master 日志
docker logs weibo_sentiment_hbase_master --tail=100

# 先起大数据 profile，再看健康状态
docker compose -f deployment/docker-compose.yml \
  --env-file deployment/.env.docker \
  --profile with-bigdata up -d
```

### 问题 4.4: 前端页面资源 404

**解决:**
```bash
# 检查前端容器与 Nginx 配置
docker logs weibo_sentiment_frontend --tail=100

# 验证首页可访问
curl -I http://127.0.0.1:3001/

# 前端单独重建
docker compose -f deployment/docker-compose.yml \
  --env-file deployment/.env.docker \
  --profile with-frontend up -d --build frontend
```

### 问题 5: 镜像构建失败 (npm/pip 超时)

**解决:**
```bash
# 已在 Dockerfile 中配置了国内镜像源
# 如果仍然超时，配置 Docker 镜像加速器:
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<EOF
{
    "registry-mirrors": [
        "https://docker.1panel.live",
        "https://mirror.ccs.tencentyun.com"
    ]
}
EOF
sudo systemctl restart docker
```

### 问题 6: 日志乱码

**解决:**
```bash
# 确保终端 UTF-8
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

# 永久设置 (写入 ~/.bashrc)
echo 'export LANG=C.UTF-8' >> ~/.bashrc
echo 'export LC_ALL=C.UTF-8' >> ~/.bashrc
source ~/.bashrc
```

### 问题 7: Windows 传来的文件换行符问题

**现象:** `/bin/bash^M: bad interpreter` 或 YAML 解析错误

**解决:**
```bash
sudo apt-get install -y dos2unix
find /root/weibo-analysis -name "*.sh" -exec dos2unix {} \;
find /root/weibo-analysis -name "*.yml" -exec dos2unix {} \;
find /root/weibo-analysis -name "*.conf" -exec dos2unix {} \;
find /root/weibo-analysis -name ".env*" -exec dos2unix {} \;
```

### 问题 8: Spark Worker 内存不足

**现象:** `java.lang.OutOfMemoryError` 或 Worker 反复重启

**解决:** 编辑 `.env.docker`:
```ini
# 减少 Spark Worker 内存 (默认已优化为 1g)
SPARK_WORKER_MEMORY=512m
SPARK_WORKER_MEMORY_LIMIT=768M
```

### 问题 9: 宿主机无法访问虚拟机服务

**排查:**
```bash
# 1. 确认虚拟机防火墙
sudo ufw status
sudo ufw allow 3001/tcp  # 前端
sudo ufw allow 5000/tcp  # Flask
sudo ufw allow 8081/tcp  # Java
sudo ufw allow 8080/tcp  # Spark UI

# 2. 检查虚拟机网络模式 (VirtualBox/VMware 需要桥接网络或端口转发)

# 3. 检查服务是否监听 0.0.0.0
ss -tlnp | grep :5000
# 应显示 0.0.0.0:5000 而不是 127.0.0.1:5000
```

### 问题 10: 1Panel 中看不到容器

**说明:** 1Panel 默认显示所有 Docker 容器，本项目容器以 `weibo_sentiment_` 开头。如果看不到：
```bash
# 确认容器是否存在
docker ps -a --filter "name=weibo_sentiment"

# 1Panel 刷新: 进入 1Panel → 容器 → 点击刷新按钮
```

---

## 六、项目架构 (Docker 容器)

```
┌─────────────────────────────────────────────────────┐
│                  Ubuntu 20.04 VM                     │
│                                                      │
│  ┌───────────┐  ┌───────────┐  ┌───────────────┐   │
│  │ Frontend  │  │ Flask API │  │ Java Backend  │   │
│  │ (Nginx)   │→ │ (Gunicorn)│  │ (Spring Boot) │   │
│  │ :3001     │  │ :5000     │  │ :8081         │   │
│  └───────────┘  └─────┬─────┘  └───────┬───────┘   │
│                       │                 │            │
│         ┌─────────────┼─────────────────┤            │
│         ▼             ▼                 ▼            │
│  ┌───────────┐  ┌───────────┐  ┌───────────────┐   │
│  │  Redis    │  │  MySQL    │  │ Spark Cluster │   │
│  │  :6379    │  │  :3306    │  │ Master :8080  │   │
│  └───────────┘  └───────────┘  │ Worker :7077  │   │
│                                 └───────────────┘   │
│  Network: weibo-net (bridge)                        │
└─────────────────────────────────────────────────────┘
```

---

## 七、安全备注

- `123456` 仅适用于开发测试环境。
- 生产环境上线前，必须修改 `DB_PASSWORD`、`DB_ROOT_PASSWORD`、`REDIS_PASSWORD`、`SECRET_KEY`、`JWT_SECRET`。
- 建议使用强随机密码，并避免将真实 `.env.docker` 提交到版本库。
