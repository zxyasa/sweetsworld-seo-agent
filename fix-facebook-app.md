# 修复 Facebook App 权限问题

## 问题原因
错误 `Invalid Scopes: manage_pages, pages_show_list` 表示你的 App 使用了已废弃的权限。

## 解决方案 1：创建新的 App（推荐）

### 步骤：

1. **访问 Meta for Developers**
   https://developers.facebook.com/apps/

2. **创建新 App**
   - 点击 "Create App"
   - 选择 "Business" 类型
   - 名称：Sweetsworld Content Agent
   - 联系邮箱：你的邮箱

3. **添加 Facebook Login 产品**
   - 在 Dashboard 找到 "Add Product"
   - 选择 "Facebook Login"
   - 点击 "Set Up"

4. **配置 App**
   - 进入 Settings → Basic
   - 添加 App Domain: `sweetsworld.com.au`
   - Privacy Policy URL: `https://sweetsworld.com.au/privacy`
   - Terms of Service URL: `https://sweetsworld.com.au/terms`

5. **切换到 Live 模式**
   - 在顶部找到 "App Mode" 开关
   - 从 "Development" 切换到 "Live"

6. **重新在 Graph API Explorer 生成 Token**
   - https://developers.facebook.com/tools/explorer/
   - 选择新创建的 App
   - 选择 "Get Page Access Token"
   - 选择权限：
     - pages_manage_posts
     - pages_read_engagement
     - pages_manage_engagement

---

## 解决方案 2：使用临时 Token（快速测试）

如果只是想快速测试，可以使用短期 Token：

1. **访问你的 Facebook Page**
   https://www.facebook.com/sweetsworld (替换为你的 Page URL)

2. **获取 Page ID**
   - 点击 "关于" (About)
   - 向下滚动找到 "Page ID"
   - 复制这个数字

3. **生成临时 User Token**
   在 Graph API Explorer:
   - 选择 "User Token"
   - 添加权限：`pages_read_engagement`
   - Generate Access Token

4. **用 User Token 获取 Page Token**
   ```bash
   curl "https://graph.facebook.com/v18.0/me/accounts?access_token=YOUR_USER_TOKEN"
   ```

   返回结果中会包含你的 Page 的 access_token

---

## 解决方案 3：使用 Meta Business Suite

最简单的方法：

1. 访问 https://business.facebook.com/
2. 进入 Business Settings
3. System Users → Add
4. 为系统用户分配 Page 权限
5. 生成 Token

---

## 推荐做法

**如果你只是想快速开始：**
→ 使用 Meta Business Suite（方案 3）

**如果你想长期使用：**
→ 创建新的 App（方案 1）

**如果你想快速测试：**
→ 使用临时 Token（方案 2）
