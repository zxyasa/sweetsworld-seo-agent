# Sweetsworld SEO Automation Agent

自动化 SEO 内容生成工具，用于为 [sweetsworld.com.au](https://sweetsworld.com.au) 创建 WordPress 草稿文章，并通过 Telegram 发送通知。

## 功能特性

### 核心功能
- ✅ 从 CSV 文件读取选题
- ✅ **双模式内容生成**：模板生成 或 AI 生成（OpenAI）
- ✅ 通过 WordPress REST API 创建草稿文章
- ✅ Telegram 消息推送（草稿链接）
- ✅ 完整的错误处理和状态反馈

### 高级功能（可选）
- 🤖 **OpenAI 集成** - AI 动态生成高质量 SEO 文章
- 📊 **Google Search Console 集成** - 获取真实搜索关键词数据
- 🎯 智能关键词优化和内容个性化

## 技术栈

- Python 3.10+
- WordPress REST API (Application Password 认证)
- Telegram Bot API
- OpenAI API (可选)
- Google Search Console API (可选)
- 依赖：`requests` + `python-dotenv` + `openai` + `google-api-python-client`

## 目录结构

```
sweetsworld-seo-agent/
├── README.md                 # 项目文档
├── .gitignore               # Git 忽略文件
├── .env.example             # 环境变量模板
├── requirements.txt         # Python 依赖
├── topics.csv               # 选题数据
├── gsc_credentials.json     # GSC 凭证（可选，需自行创建）
└── src/
    ├── config.py            # 配置管理
    ├── wp_client.py         # WordPress API 客户端
    ├── content_generator.py # 内容生成器（支持模板+AI）
    ├── openai_generator.py  # OpenAI 集成
    ├── gsc_client.py        # Google Search Console 集成
    ├── telegram_notify.py   # Telegram 通知
    └── run_mvp.py           # 主程序入口
```

## 快速开始

### 1. 环境准备

```bash
# 克隆或进入项目目录
cd sweetsworld-seo-agent

# 创建 Python 虚拟环境
python3 -m venv .venv

# 激活虚拟环境
# macOS/Linux:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# WordPress 配置
WP_BASE_URL="https://sweetsworld.com.au"
WP_USERNAME="your_actual_username"
WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"

# Telegram 配置（可选）
TELEGRAM_BOT_TOKEN="your_bot_token"
TELEGRAM_CHAT_ID="your_chat_id"
```

#### 获取 WordPress Application Password

1. 登录 WordPress 管理后台
2. 进入 **Users** → **Profile** (或直接访问 `/wp-admin/profile.php`)
3. 滚动到页面底部的 **Application Passwords** 部分
4. 输入应用名称（如 "SEO Automation Agent"）
5. 点击 **Add New Application Password**
6. 复制生成的密码（格式：`xxxx xxxx xxxx xxxx xxxx xxxx`）
7. 粘贴到 `.env` 文件的 `WP_APP_PASSWORD` 中

**注意：** 密码只显示一次，请妥善保存！

#### 获取 Telegram Bot Token（可选）

1. 在 Telegram 中搜索 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot` 创建新 Bot
3. 按提示设置 Bot 名称和用户名
4. 获取 Bot Token 并填入 `.env`
5. 搜索 [@userinfobot](https://t.me/userinfobot) 获取你的 Chat ID

#### 配置 OpenAI API（可选 - AI 内容生成）

如果希望使用 AI 动态生成文章内容，需要配置 OpenAI API：

1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 登录并进入 **API Keys** 页面
3. 点击 **Create new secret key** 生成 API Key
4. 复制 API Key 并添加到 `.env` 文件：

```env
OPENAI_API_KEY="sk-proj-..."
OPENAI_MODEL="gpt-4o"
USE_AI_GENERATION="true"
```

**注意：**
- 设置 `USE_AI_GENERATION="true"` 启用 AI 生成
- 设置为 `"false"` 或留空则使用模板生成（免费）
- 推荐模型：`gpt-4o`（性价比高）或 `gpt-4-turbo`
- OpenAI API 按使用量计费，请注意成本控制

#### 配置 Google Search Console（可选 - 关键词数据）

如果希望从 GSC 获取真实搜索关键词数据来优化内容：

1. **创建 Google Cloud 项目**
   - 访问 [Google Cloud Console](https://console.cloud.google.com/)
   - 创建新项目或选择现有项目

2. **启用 Search Console API**
   - 在项目中搜索并启用 **Google Search Console API**

3. **创建服务账号**
   - 进入 **IAM & Admin** → **Service Accounts**
   - 创建服务账号（名称如 "SEO Agent"）
   - 点击服务账号 → **Keys** → **Add Key** → **Create new key**
   - 选择 **JSON** 格式下载凭证文件
   - 将文件重命名为 `gsc_credentials.json` 并放到项目根目录

4. **授权服务账号访问 Search Console**
   - 登录 [Google Search Console](https://search.google.com/search-console)
   - 选择你的网站属性（sweetsworld.com.au）
   - 进入 **Settings** → **Users and permissions**
   - 点击 **Add user**，输入服务账号邮箱（格式：`xxx@xxx.iam.gserviceaccount.com`）
   - 权限选择 **Full**，点击 **Add**

5. **配置 .env 文件**
```env
GSC_PROPERTY_URL="https://sweetsworld.com.au"
GSC_CREDENTIALS_FILE="gsc_credentials.json"
USE_GSC_DATA="true"
```

**注意：**
- GSC 数据需要网站已有一定搜索流量
- 新网站可能没有足够数据，建议先使用模板生成
- 设置 `USE_GSC_DATA="false"` 可禁用 GSC 集成

### 3. 准备选题数据

编辑 `topics.csv` 文件，添加你的选题：

```csv
slug,title,primary_keyword,category_hint
wholesale-candy-australia-guide,Wholesale Candy Australia: Supplier Guide (2026),wholesale candy australia,Wholesale Candy
sour-lollies-buying-guide,Sour Lollies Buying Guide: Flavours, Brands & Bulk,sour lollies australia,Sour Lollies
```

**字段说明：**
- `slug`: URL 友好的文章标识符（将作为永久链接）
- `title`: 文章标题
- `primary_keyword`: 主要 SEO 关键词
- `category_hint`: 分类提示（用于内容生成）

### 4. 运行程序

```bash
python src/run_mvp.py
```

**预期输出：**

```
🚀 SEO Automation Agent MVP - Starting...

✅ Configuration loaded
   WordPress: https://sweetsworld.com.au
   Username: your_username

📋 Found 2 topics to process

[1/2] Processing: Wholesale Candy Australia: Supplier Guide (2026)
  ✅ Generated HTML content (3456 characters)
  ✅ Created draft: https://sweetsworld.com.au/?p=123

[2/2] Processing: Sour Lollies Buying Guide: Flavours, Brands & Bulk
  ✅ Generated HTML content (3521 characters)
  ✅ Created draft: https://sweetsworld.com.au/?p=124

📤 Sending Telegram notification...
✅ Telegram notification sent successfully

==================================================
✅ Done. Created drafts: 2/2
==================================================
```

## 成功标准

运行成功后，你应该看到：

1. ✅ WordPress 后台出现新的草稿文章（状态为 Draft）
2. ✅ Telegram 收到包含草稿链接的通知消息
3. ✅ 控制台输出显示所有文章创建成功

## 常见问题排查

### 401 Unauthorized

**原因：** WordPress 认证失败

**解决方案：**
- 检查 `WP_USERNAME` 是否正确
- 确认 `WP_APP_PASSWORD` 格式正确（包含空格）
- 验证 Application Password 未过期或被删除
- 确保用户有发布文章的权限

### 403 Forbidden

**原因：** 权限不足或 REST API 被禁用

**解决方案：**
- 确认用户角色为 Editor 或 Administrator
- 检查 WordPress 是否启用了 REST API
- 查看是否有安全插件阻止 API 访问

### 404 Not Found

**原因：** WordPress REST API 不可用

**解决方案：**
- 确认 `WP_BASE_URL` 正确（不要包含尾部斜杠）
- 访问 `https://sweetsworld.com.au/wp-json/wp/v2/posts` 测试 API
- 检查 WordPress 固定链接设置是否正确

### Connection Error

**原因：** 网络连接问题

**解决方案：**
- 检查网络连接
- 确认网站可正常访问
- 尝试增加请求超时时间（修改 `wp_client.py` 中的 `timeout` 参数）

## 功能清单

### ✅ 已实现
- [x] WordPress REST API 集成（草稿创建）
- [x] 完善的错误处理（401/403/404/500）
- [x] 模板式内容生成
- [x] **OpenAI API 集成**（AI 动态内容生成）
- [x] **Google Search Console 集成**（真实关键词数据）
- [x] Telegram 通知推送
- [x] CSV 批量处理

### 🚀 后续扩展计划
- [ ] 自动获取 WooCommerce 产品数据并插入文章
- [ ] 支持自动设置特色图片（Unsplash/Pexels）
- [ ] 支持自动分类和标签
- [ ] 添加内容质量检查和 SEO 评分
- [ ] 支持批量更新已有文章
- [ ] 定时任务和自动化执行
- [ ] 内容 A/B 测试

## 开发环境

- Python 3.10+
- VS Code (推荐)
- Git

## License

MIT

## 联系方式

如有问题，请通过 GitHub Issues 反馈。
