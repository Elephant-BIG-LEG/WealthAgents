# WealthAgents - 智能投研多Agent系统

WealthAgents是一个基于大语言模型和多Agent技术的智能投研系统，能够自动采集财经数据、分析市场热点、生成投资报告，并提供交互式Web界面。

## 🚀 核心功能

### 🔍 智能数据采集
- 多源财经数据自动采集（东方财富网、新浪财经等）
- 支持自动翻页和批量数据获取
- 结构化数据提取与清洗

### 🤖 多Agent智能协作
- **规划Agent**：任务分解与规划
- **执行Agent**：任务执行与监控
- **反思Agent**：结果评估与优化
- **记忆Agent**：上下文管理与记忆存储
- 基于LangGraph的Plan-Act-Reflect决策闭环

### 💡 高级AI能力
- 自然语言理解与意图识别
- 基于SBERT的文本向量化
- 增强版RAG（检索增强生成）
- 智能工具调用与路由
- 多轮对话与上下文管理

### 📊 数据分析与可视化
- 财经新闻自动摘要
- 市场热点分析与追踪
- 财务数据深度解析
- 投资风险评估

### 🌐 交互式Web界面
- 直观的数据采集与分析界面
- 实时任务监控与状态展示
- 投资报告自动生成与下载
- 多Agent协作可视化

## 🛠️ 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| **核心框架** | Python | 3.8+ |
| **Web框架** | Flask | - |
| **AI框架** | LangChain, LangGraph | - |
| **向量存储** | FAISS | - |
| **数据库** | MySQL | 8.0+ |
| **LLM API** | DashScope (阿里云百炼) | - |
| **向量化模型** | Sentence-BERT | - |

## 📦 快速开始

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

复制示例配置文件并填写相关信息：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置数据库和API密钥：

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=FinanceData

# DashScope API配置
DASHSCOPE_API_KEY=your_api_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/api/v1

# OpenAI兼容API（可选）
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 4. 初始化数据库

```bash
python init_database.py
```

### 5. 启动应用

运行主程序：

```bash
python main.py
```

然后选择启动模式：
- 输入 `1` 启动命令行模式
- 输入 `2` 启动Web界面模式
- 输入 `3` 启动向量化测试模式
- 输入 `4` 启动Faiss向量数据库测试模式

### 6. 访问Web界面

选择Web界面模式后，访问以下地址：

```
http://localhost:5001
```

## 📁 项目结构

```
WealthAgents/
├── app/                    # 应用核心代码
│   ├── Embedding/          # 文本向量化模块
│   ├── agent/              # 智能Agent核心
│   │   ├── multi_agent/    # 多Agent协作系统
│   │   ├── tools/          # 工具集
│   │   ├── adapters/       # 外部系统适配器
│   │   └── ...             # Agent核心组件
│   ├── agentWorker/        # Agent工作线程
│   ├── api/                # RESTful API
│   ├── chunk/              # 文本分割模块
│   ├── ingest/             # 数据采集模块
│   ├── parse/              # 数据解析模块
│   ├── retrieval/          # 信息检索模块
│   ├── services/           # 业务服务
│   ├── store/              # 数据存储
│   ├── ui/                 # Web界面
│   └── utils/              # 工具函数
├── faiss_database/         # 向量数据库
├── .env.example            # 环境变量示例
├── main.py                 # 主入口文件
└── requirements.txt        # 依赖列表
```

## 🤝 使用示例

### Web界面使用

1. **访问首页**：打开浏览器访问 `http://localhost:5001`
2. **数据采集**：在数据采集页面输入关键词和数据源，点击"开始采集"
3. **市场分析**：在市场热点页面查看AI自动生成的热点分析
4. **任务监控**：实时查看任务执行状态和进度
5. **报告生成**：查看自动生成的投资分析报告

### 命令行使用

```bash
# 启动命令行模式
python main.py
# 然后输入 1 选择命令行模式
```

### API调用示例

```bash
# 采集财经数据
curl -X POST http://localhost:5001/api/v1/collect \
  -H "Content-Type: application/json" \
  -d '{"query": "市场热点", "source": "eastmoney"}'

# 获取采集结果
curl -X GET http://localhost:5001/api/v1/get_data?query=市场热点
```

## 🧠 核心模块说明

### Agent系统

- **Plan-Act-Reflect**：基于LangGraph的决策闭环
- **MemoryManager**：双重存储后端（Redis + 内存）
- **ToolRouter**：智能工具选择与调用
- **StateMachine**：显式状态管理与流转

### 多Agent协作

- **协调器**：多Agent通信与协调
- **辩论机制**：冲突检测与多轮证据交换
- **协商机制**：投票/妥协达成共识
- **消息总线**：统一的Agent通信渠道

### 智能工具

- `web_scraping_tool`：网页数据采集
- `data_analysis`：数据分析与处理
- `financial_report_adapter`：财报数据获取
- `market_data_adapter`：市场数据获取
- `risk_assessment`：风险评估

## 📈 应用场景

- **财经新闻监控**：自动采集和分析财经新闻
- **市场热点追踪**：实时追踪和分析市场热点
- **投资决策支持**：生成投资建议和报告
- **财务数据分析**：深度解析上市公司财务数据
- **投资风险评估**：评估投资项目风险

## 🤗 贡献指南

我们欢迎社区贡献！以下是贡献步骤：

1. Fork 本项目
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送到分支：`git push origin feature/AmazingFeature`
5. 提交Pull Request

### 开发规范

- 遵循PEP 8代码规范
- 为新功能添加测试
- 更新文档
- 确保所有测试通过

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 📞 联系方式

- 项目地址：[GitHub Repository](<your-repo-url>)
- 问题反馈：[Issues](<your-repo-url>/issues)
- 建议和改进：[Discussions](<your-repo-url>/discussions)

## 🙏 致谢

感谢所有为本项目做出贡献的开发者和社区成员！

---

**WealthAgents** - 让投资更智能，让决策更高效！ 🚀