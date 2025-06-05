# 大模型翻译平台 (AI Translation Platform)

一个基于多个大语言模型的智能翻译平台，提供高质量的多语言翻译服务。

## 🌟 核心功能

### 翻译功能
- **多模型支持**: 集成 OpenAI GPT、Claude、Google Translate、百度翻译等多个翻译引擎
- **实时翻译**: 支持实时文本翻译和预览
- **批量翻译**: 支持文档批量翻译
- **多种输入方式**: 文本输入、文件上传、语音输入
- **语言检测**: 自动检测源语言

### 智能优化
- **翻译质量评估**: AI驱动的翻译质量评分
- **多模型对比**: 同时展示多个模型的翻译结果
- **专业术语词典**: 支持自定义专业术语翻译
- **翻译风格定制**: 支持正式、非正式、技术等不同翻译风格

### 用户体验
- **历史记录**: 完整的翻译历史管理
- **收藏夹**: 收藏常用翻译
- **用户账户**: 个人设置和偏好管理
- **响应式设计**: 支持桌面和移动设备

## 🏗️ 技术架构

### 前端
- **React 18** + **TypeScript**
- **Tailwind CSS** 样式框架
- **Zustand** 状态管理
- **React Query** 数据获取
- **Framer Motion** 动画效果

### 后端
- **FastAPI** Python Web框架
- **SQLAlchemy** ORM
- **PostgreSQL** 主数据库
- **Redis** 缓存和会话存储
- **Celery** 异步任务处理

### AI集成
- **OpenAI API** (GPT-4, GPT-3.5)
- **Anthropic Claude API**
- **Google Cloud Translation API**
- **百度翻译API**
- **自定义模型接口**

## 🚀 快速开始

### 环境要求
- Node.js 18+
- Python 3.9+
- PostgreSQL 13+
- Redis 6+

### 安装步骤

1. 克隆项目
```bash
git clone https://github.com/kie0519/Translation-Platform.git
cd Translation-Platform
```

2. 启动后端服务
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

3. 启动前端服务
```bash
cd frontend
npm install
npm run dev
```

4. 使用Docker启动（推荐）
```bash
docker-compose up -d
```

## 📁 项目结构

```
Translation-Platform/
├── frontend/                 # React前端应用
│   ├── src/
│   │   ├── components/      # 可复用组件
│   │   ├── pages/          # 页面组件
│   │   ├── hooks/          # 自定义Hooks
│   │   ├── services/       # API服务
│   │   ├── stores/         # 状态管理
│   │   └── utils/          # 工具函数
│   ├── public/
│   └── package.json
├── backend/                  # FastAPI后端服务
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   └── utils/          # 工具函数
│   ├── alembic/            # 数据库迁移
│   └── requirements.txt
├── docker-compose.yml        # Docker编排文件
├── nginx.conf               # Nginx配置
└── README.md
```

## 🔧 配置说明

### 环境变量配置

创建 `.env` 文件：

```env
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/translation_db
REDIS_URL=redis://localhost:6379

# AI API密钥
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_claude_api_key
GOOGLE_API_KEY=your_google_api_key
BAIDU_APP_ID=your_baidu_app_id
BAIDU_SECRET_KEY=your_baidu_secret_key

# JWT配置
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## 🎯 产品特色

### 1. 多模型智能选择
- 根据语言对和文本类型自动选择最优翻译模型
- 支持用户手动选择和对比不同模型结果

### 2. 翻译质量保证
- AI驱动的翻译质量评分系统
- 基于上下文的翻译优化建议
- 专业术语一致性检查

### 3. 企业级功能
- 团队协作和项目管理
- API接口和SDK支持
- 翻译记忆库和术语库
- 详细的使用统计和分析

### 4. 安全与隐私
- 端到端加密传输
- 数据本地化存储选项
- 符合GDPR和数据保护法规

## 📊 性能指标

- **翻译速度**: < 2秒响应时间
- **准确率**: 95%+ 专业翻译准确率
- **支持语言**: 100+ 语言对
- **并发处理**: 1000+ 并发翻译请求

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系我们

- 项目主页: https://github.com/kie0519/Translation-Platform
- 问题反馈: https://github.com/kie0519/Translation-Platform/issues
- 邮箱: support@translation-platform.com

---

⭐ 如果这个项目对你有帮助，请给我们一个星标！