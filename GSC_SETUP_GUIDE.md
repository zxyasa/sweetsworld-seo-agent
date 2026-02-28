# Google Search Console API 设置指南

## 📋 问题

运行 `seo_discover` 时出现错误：
```
❌ 发现失败: GSC credentials file not found: gsc_credentials.json
```

## ✅ 解决方法

你需要从 Google Cloud Console 下载服务账号凭证文件。

---

## 🔧 完整设置步骤

### 步骤 1: 创建服务账号（如果还没有）

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 选择你的项目（或创建新项目）
3. 导航到：**IAM & Admin** > **Service Accounts**
4. 点击 **Create Service Account**
5. 填写信息：
   - Name: `SEO Agent`
   - Description: `Service account for sweetsworld SEO automation`
6. 点击 **Create and Continue**
7. 跳过权限设置（点击 **Continue**）
8. 点击 **Done**

### 步骤 2: 下载凭证文件

1. 在 Service Accounts 列表中，找到刚创建的账号
2. 点击账号邮箱（例如：`seo-agent@...iam.gserviceaccount.com`）
3. 切换到 **Keys** 标签
4. 点击 **Add Key** > **Create new key**
5. 选择 **JSON** 格式
6. 点击 **Create**
7. JSON 文件会自动下载到你的电脑

### 步骤 3: 移动凭证文件

将下载的 JSON 文件移动到正确位置并重命名：

```bash
# 假设文件下载到了 ~/Downloads/项目名-xxxxx.json
mv ~/Downloads/项目名-xxxxx.json ~/agents/sweetsworld-seo-agent/gsc_credentials.json
```

或者手动：
1. 找到下载的 JSON 文件
2. 重命名为 `gsc_credentials.json`
3. 移动到 `/Users/michaelzhao/agents/agents/sweetsworld-seo-agent/` 目录

### 步骤 4: 在 Search Console 中授权服务账号

1. 访问 [Google Search Console](https://search.google.com/search-console)
2. 选择你的网站属性（`sweetsworld.com.au`）
3. 点击 **Settings** (⚙️) > **Users and permissions**
4. 点击 **Add user**
5. 输入服务账号邮箱：`seo-agent@...iam.gserviceaccount.com`
   - 你可以在 JSON 文件中找到这个邮箱（`client_email` 字段）
6. 权限选择：**Full** 或 **Restricted**（推荐 Full 以访问所有数据）
7. 点击 **Add**

### 步骤 5: 验证设置

运行测试脚本：

```bash
cd ~/agents/sweetsworld-seo-agent
source .venv/bin/activate
python -c "from src.gsc_client import GSCClient; from src.config import get_settings; s = get_settings(); c = GSCClient(s.gsc_property_url, s.gsc_credentials_file); print('✅ GSC 连接成功')"
```

如果成功，会显示：
```
✅ GSC 连接成功
```

---

## 🔍 替代方案：使用主题模式（无需 GSC）

如果你暂时不想设置 GSC，可以使用主题模式来发现内容机会：

在 Telegram 发送：
```
"发现关于 chocolate 的内容机会"
"发现关于 vegan candy 的内容机会"
```

这会使用 OpenAI 基于市场趋势生成建议，无需 GSC 数据。

---

## 📊 GSC vs 主题模式对比

| 特性 | GSC 模式 | 主题模式 |
|------|---------|---------|
| **数据来源** | 你的真实 GSC 数据 | OpenAI 趋势预测 |
| **精准度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **设置难度** | 需要配置凭证 | 无需配置 |
| **适用场景** | 优化现有流量 | 探索新领域 |

---

## ⚠️ 安全提示

1. **不要分享凭证文件**
   - `gsc_credentials.json` 包含敏感信息
   - 已添加到 `.gitignore`，不会提交到 Git

2. **定期轮换密钥**
   - 建议每 90 天轮换一次服务账号密钥

3. **最小权限原则**
   - 服务账号只授予必要的权限

---

## 🛠️ 故障排除

### 问题 1: "Permission denied"

**原因：** 服务账号未在 Search Console 中授权

**解决：**
1. 检查 Search Console > Settings > Users
2. 确认服务账号邮箱已添加
3. 确认权限为 Full 或 Restricted

### 问题 2: "Invalid credentials"

**原因：** JSON 文件格式错误或损坏

**解决：**
1. 重新下载凭证文件
2. 确认文件是完整的 JSON 格式
3. 不要手动编辑 JSON 文件

### 问题 3: "Property not found"

**原因：** `.env` 中的 `GSC_PROPERTY_URL` 不正确

**解决：**
```bash
# 检查 .env 配置
cat ~/agents/sweetsworld-seo-agent/.env | grep GSC_PROPERTY_URL

# 应该是：
GSC_PROPERTY_URL=sc-domain:sweetsworld.com.au

# 不是：
GSC_PROPERTY_URL=https://sweetsworld.com.au
```

---

## 📚 相关文档

- [Google Cloud Service Accounts](https://cloud.google.com/iam/docs/service-accounts)
- [Search Console API](https://developers.google.com/webmaster-tools/search-console-api-original)
- [Python Client Library](https://github.com/googleapis/google-api-python-client)

---

## ✅ 快速检查清单

- [ ] 创建了 Google Cloud 服务账号
- [ ] 下载了 JSON 凭证文件
- [ ] 移动文件到 `~/agents/sweetsworld-seo-agent/gsc_credentials.json`
- [ ] 在 Search Console 中授权了服务账号邮箱
- [ ] 运行测试脚本验证连接
- [ ] 在 Telegram 测试 `seo_discover`

---

需要帮助？检查错误日志：
```bash
tail -100 ~/agents/tg_agent/bot.stderr.log
```
