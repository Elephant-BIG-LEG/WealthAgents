# WealthAgents - 财经数据采集与分析系统

这是一个基于Python的财经数据采集与分析系统，可以从东方财富网等财经网站采集数据，并使用大语言模型进行分析和总结。

## 功能特性

- 🕷️ 网页数据采集（支持自动翻页）
- 🤖 大语言模型数据清洗与解析
- 📊 数据分析与总结
- 💾 MySQL数据库存储
- 🌐 Web界面展示

## 系统架构

```
WealthAgents/
├── app/                    # 应用核心代码
│   ├── ingest/            # 数据采集模块
│   ├── parse/             # 数据解析模块
│   ├── agentWorker/       # 大模型处理模块
│   ├── services/          # 业务服务模块
│   ├── store/             # 数据存储模块
│   ├── ui/                # Web界面模块
│   └── config/            # 配置模块
├── faiss_database/        # 向量数据库
└── init_database.py       # 数据库初始化脚本
```

## 环境要求

- Python 3.8+
- MySQL 8.0+
- DashScope API Key (阿里云百炼平台)

## 安装部署

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd WealthAgents
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 文件并重命名为 `.env`，然后填写相应的配置信息：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的配置信息：

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=13306
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=FinanceData

# DashScope API配置
DASHSCOPE_API_KEY=your_api_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/api/v1
```

### 4. 初始化数据库

```bash
python init_database.py
```

### 5. 启动应用

```bash
python app/ui/web_app.py
```

访问 `http://localhost:5001` 使用Web界面。

## 安全说明

### 敏感信息保护

项目中的敏感信息（如数据库密码、API密钥等）存储在环境变量中，不会上传到Git仓库。

- `.env` 文件已被添加到 `.gitignore` 中，不会被上传
- 请确保在生产环境中妥善保管 `.env` 文件
- 可以参考 `.env.example` 文件创建自己的配置文件

### 数据库安全

- 建议为数据库用户设置最小权限原则
- 不要在代码中硬编码敏感信息
- 定期更换密码和API密钥

## 项目结构说明

### 核心模块

1. **数据采集模块** (`app/ingest/`)
   - `web_fetcher.py`: 网页数据采集器
   - `source.py`: 数据源定义

2. **数据解析模块** (`app/parse/`)
   - `parsing.py`: 数据清洗和解析

3. **大模型处理模块** (`app/agentWorker/`)
   - `data_parse_and_process.py`: 数据清洗和结构化处理
   - `data_summarizer.py`: 数据总结和分析

4. **业务服务模块** (`app/services/`)
   - `parse_service.py`: 解析服务
   - `splitter_service.py`: 文本分割服务
   - `vectorize_service.py`: 向量化服务

5. **数据存储模块** (`app/store/`)
   - `database_service.py`: 数据库连接服务
   - `faiss_store.py`: 向量数据库存储

6. **Web界面模块** (`app/ui/`)
   - `web_app.py`: Flask Web应用
   - `templates/`: HTML模板文件

### 配置模块

- `app/config/config.py`: 配置文件加载和管理

## 使用说明

### Web界面操作

1. 访问 `http://localhost:5001`
2. 在输入框中填写要采集的网址和数据源名称
3. 点击"开始采集"按钮
4. 系统会自动采集数据并进行分析
5. 在结果区域查看分析结果

### API接口

系统还提供了RESTful API接口：

- `POST /collect`: 采集数据
- `GET /get_data`: 获取采集的数据
- `POST /clear_data`: 清除数据

## 贡献指南

欢迎提交Issue和Pull Request来改进这个项目。

## 许可证

MIT License

## 联系方式

如有问题，请提交Issue或联系项目维护者。