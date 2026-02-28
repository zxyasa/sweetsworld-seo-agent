# 社交媒体 API 配置指南

本指南将帮助你获取所有社交媒体平台的 API 凭证。

---

## 📘 Facebook Page Access Token

### 步骤 1：创建 Facebook App

1. 访问 [Facebook Developers](https://developers.facebook.com/)
2. 登录你的 Facebook 账号
3. 点击 **My Apps** → **Create App**
4. 选择 **Business** 类型
5. 填写 App 名称（如 "Sweetsworld Content Agent"）
6. 创建应用

### 步骤 2：添加 Pages API 权限

1. 在你的 App 中，找到 **Add Product**
2. 添加 **Facebook Login** 和 **Pages API**
3. 进入 **Settings** → **Basic**，记录 **App ID** 和 **App Secret**

### 步骤 3：获取 Page Access Token

1. 进入 [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. 选择你刚创建的 App
3. 点击 **User or Page** → 选择你的 Page
4. 添加权限：
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_posts`
   - `pages_manage_engagement`
5. 点击 **Generate Access Token**
6. 复制 Access Token

### 步骤 4：获取 Page ID

1. 访问你的 Facebook Page
2. 进入 **Settings** → **Page Info**
3. 复制 **Page ID**

### 步骤 5：将 Token 转换为永久 Token（重要）

临时 Token 会在几小时后过期，需要转换为长期 Token：

```bash
curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=YOUR_SHORT_LIVED_TOKEN"
```

将返回的 `access_token` 添加到 `.env`：

```env
FACEBOOK_PAGE_ID=你的Page ID
FACEBOOK_ACCESS_TOKEN=长期Access Token
```

---

## 📷 Instagram Business Account

### 前提条件
- 你的 Instagram 账号必须是 **Business Account**
- 必须已连接到 Facebook Page

### 步骤 1：转换为 Business Account

1. 打开 Instagram App
2. 进入 **Settings** → **Account**
3. 点击 **Switch to Professional Account**
4. 选择 **Business**
5. 连接到你的 Facebook Page

### 步骤 2：获取 Instagram Business ID

1. 使用上面获取的 Facebook Page Access Token
2. 运行以下命令：

```bash
curl -X GET "https://graph.facebook.com/v18.0/YOUR_PAGE_ID?fields=instagram_business_account&access_token=YOUR_PAGE_ACCESS_TOKEN"
```

3. 返回的 `instagram_business_account.id` 就是你的 Instagram Business ID

添加到 `.env`：

```env
INSTAGRAM_BUSINESS_ID=你的Instagram Business ID
```

**注意：** Instagram 发布需要使用 Facebook 的 Access Token（已在上面配置）

---

## 🐦 X (Twitter) API

### 步骤 1：申请 Developer Account

1. 访问 [Twitter Developer Portal](https://developer.twitter.com/)
2. 登录你的 X 账号
3. 点击 **Sign up** 申请开发者账号
4. 填写使用目的（建议选择 "Building tools for myself"）
5. 等待审核（通常几分钟到几小时）

### 步骤 2：创建 App

1. 审核通过后，进入 [Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. 点击 **Create Project**
3. 填写项目名称和描述
4. 创建一个 App（如 "Sweetsworld Bot"）

### 步骤 3：获取 Bearer Token

1. 进入你的 App 设置
2. 找到 **Keys and tokens** 标签
3. 在 **Authentication Tokens** 部分，找到 **Bearer Token**
4. 如果没有，点击 **Regenerate** 生成新的

### 步骤 4：设置权限

1. 进入 **App Settings** → **User authentication settings**
2. 点击 **Set up**
3. 选择 **Read and write** 权限
4. 保存设置

添加到 `.env`：

```env
X_BEARER_TOKEN=你的Bearer Token
```

**注意：**
- 免费 API 有发推限制（每月 1,500 条）
- 需要付费升级到 Basic ($100/月) 才能自动发推

---

## 📌 Pinterest API

### 步骤 1：创建 Pinterest App

1. 访问 [Pinterest Developers](https://developers.pinterest.com/)
2. 登录你的 Pinterest Business 账号
3. 点击 **My Apps** → **Create App**
4. 填写 App 信息

### 步骤 2：获取 Access Token

1. 进入你的 App
2. 找到 **OAuth** 标签
3. 生成 **Access Token**
4. 确保勾选以下权限：
   - `boards:read`
   - `pins:read`
   - `pins:write`

添加到 `.env`：

```env
PINTEREST_ACCESS_TOKEN=你的Access Token
```

---

## 🏢 Google Business Profile (Google 我的商家)

### 步骤 1：创建 Google Cloud Project

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目（如 "Sweetsworld GBP Integration"）

### 步骤 2：启用 API

1. 在项目中搜索并启用：
   - **Google My Business API**
   - **Google Business Profile API**

### 步骤 3：创建 OAuth 2.0 凭证

1. 进入 **APIs & Services** → **Credentials**
2. 点击 **Create Credentials** → **OAuth client ID**
3. 选择 **Web application**
4. 添加授权重定向 URI：`http://localhost:8787/oauth/callback`
5. 记录 **Client ID** 和 **Client Secret**

### 步骤 4：获取 Refresh Token

运行以下脚本获取授权：

```bash
# 1. 生成授权 URL
echo "https://accounts.google.com/o/oauth2/v2/auth?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:8787/oauth/callback&response_type=code&scope=https://www.googleapis.com/auth/business.manage&access_type=offline&prompt=consent"

# 2. 在浏览器中打开上面的 URL，授权后会跳转到 localhost 并在 URL 中看到 code 参数

# 3. 用 code 换取 refresh token
curl -X POST https://oauth2.googleapis.com/token \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "code=YOUR_AUTH_CODE" \
  -d "grant_type=authorization_code" \
  -d "redirect_uri=http://localhost:8787/oauth/callback"
```

### 步骤 5：获取 Account ID 和 Location ID

```bash
# 使用 access token 获取账号信息
curl -X GET "https://mybusinessaccountmanagement.googleapis.com/v1/accounts" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 获取位置信息
curl -X GET "https://mybusinessbusinessinformation.googleapis.com/v1/accounts/YOUR_ACCOUNT_ID/locations" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

添加到 `.env`：

```env
GBP_ACCOUNT_ID=你的Account ID
GBP_LOCATION_ID=你的Location ID
GOOGLE_OAUTH_CLIENT_ID=你的Client ID
GOOGLE_OAUTH_CLIENT_SECRET=你的Client Secret
GOOGLE_OAUTH_REFRESH_TOKEN=你的Refresh Token
```

---

## 🧪 测试配置

配置完成后，将 `PUBLISH_MODE` 保持为 `dry_run` 进行测试：

```bash
# 测试 webhook
curl -X POST http://localhost:8787/webhook/wp \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Post",
    "slug": "test-post",
    "url": "https://sweetsworld.com.au/test-post",
    "excerpt": "This is a test",
    "image": "https://example.com/image.jpg"
  }'
```

检查日志确认配置正确后，修改为 `live` 模式：

```env
PUBLISH_MODE=live
```

---

## 📊 API 费用对比

| 平台 | 免费额度 | 付费计划 |
|------|----------|----------|
| **Facebook** | ✅ 完全免费 | - |
| **Instagram** | ✅ 完全免费 | - |
| **X (Twitter)** | ⚠️ 1,500 推文/月 | $100/月 (Basic) |
| **Pinterest** | ✅ 完全免费 | - |
| **Google Business** | ✅ 完全免费 | - |

---

## ⚠️ 重要提示

1. **保护你的 API Keys**
   - 永远不要将 `.env` 文件提交到 Git
   - 定期轮换 Access Tokens
   - 使用环境变量管理敏感信息

2. **API 限制**
   - Facebook: 200 次调用/小时/用户
   - Instagram: 200 次调用/小时/用户
   - X: 1,500 推文/月（免费）
   - Pinterest: 1,000 次调用/天
   - Google: 每日 25,000 次请求

3. **测试建议**
   - 始终先用 `dry_run` 模式测试
   - 在测试账号上验证功能
   - 监控 API 使用量避免超限

---

## 🆘 需要帮助？

如果在配置过程中遇到问题：

1. 检查 API 权限是否正确
2. 确认账号类型（Business/Personal）
3. 查看平台的 API 文档
4. 联系平台支持

配置完成后运行：
```bash
npm run dev
```

祝你配置顺利！🚀
