# Sweetsworld Content Distribution Agent

Auto-publish WordPress blog posts to social media platforms.

## Setup

1. Clone the repo and install dependencies:
   ```bash
   npm install
   ```

2. Copy `.env.example` to `.env` and fill in your API tokens:
   ```bash
   cp .env.example .env
   ```

3. Build the project:
   ```bash
   npm run build
   ```

## Running

- Start the server:
  ```bash
  npm run dev
  ```

- Health check:
  ```bash
  curl http://localhost:8787/health
  ```

- Test webhook:
  ```bash
  curl -X POST http://localhost:8787/webhook/wp \
    -H "Content-Type: application/json" \
    -d '{
      "title": "Delicious Chocolate Cake Recipe",
      "url": "https://sweetsworld.com.au/chocolate-cake",
      "slug": "chocolate-cake",
      "excerpt": "Learn how to bake the perfect chocolate cake.",
      "image": "https://sweetsworld.com.au/images/cake.jpg"
    }'
  ```

- CLI publish:
  ```bash
  npm run cli -- --url "https://sweetsworld.com.au/chocolate-cake" --title "Chocolate Cake" --slug "chocolate-cake" --excerpt "Perfect cake recipe" --dry-run
  ```

## Change Recording

Every code, config, content, and manual WordPress change should be recorded in [CHANGELOG.md](CHANGELOG.md).

Use the helper script to append a standardized entry:

```bash
.venv/bin/python scripts/log_change.py \
  --type manual \
  --scope "Rank Math sitemap" \
  --summary "Refreshed sitemap index" \
  --details "post-sitemap.xml lastmod updated and previously missing URLs returned"
```

## WordPress Integration

Add this to your `functions.php` or create a plugin:

```php
add_action('publish_post', 'send_to_social_agent', 10, 2);

function send_to_social_agent($ID, $post) {
    if ($post->post_type !== 'post') return;

    $data = array(
        'title' => get_the_title($ID),
        'url' => get_permalink($ID),
        'slug' => $post->post_name,
        'excerpt' => get_the_excerpt($ID),
        'image' => get_the_post_thumbnail_url($ID, 'full')
    );

    wp_remote_post('https://YOUR-SERVER/webhook/wp', array(
        'body' => json_encode($data),
        'headers' => array('Content-Type' => 'application/json'),
    ));
}
```

## API Tokens

- **Facebook**: Get Page Access Token from Meta for Developers
- **Instagram**: Business Account ID from Meta
- **X (Twitter)**: Bearer Token from Developer Portal
- **Pinterest**: Access Token from Pinterest API
- **Google Business Profile**: OAuth credentials from Google Cloud Console

Set `PUBLISH_MODE=live` to enable actual posting (default is dry-run).

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

### 3. Prepare Topic Data

You now have two ways to maintain `topics.csv`.

#### Option A: Edit `topics.csv` manually

```csv
slug,title,primary_keyword,category_hint
wholesale-candy-australia-guide,Wholesale Candy Australia: Supplier Guide (2026),wholesale candy australia,Wholesale Candy
sour-lollies-buying-guide,"Sour Lollies Buying Guide: Flavours, Brands & Bulk",sour lollies australia,Sour Lollies
```

Field meanings:
- `slug`: URL-safe article identifier
- `title`: article title
- `primary_keyword`: main SEO keyword
- `category_hint`: article category hint

#### Option B: Let the program replenish `topics.csv`

When `AUTO_GENERATE_TOPICS=true` or `--generate-topics` is passed, the Python workflow checks how many pending rows remain before publishing. If the queue is below the target, it generates new topic ideas and appends unique rows into `topics.csv`.

Relevant settings:

```env
AUTO_GENERATE_TOPICS=true
TOPIC_GENERATION_SOURCE=auto
TOPIC_TARGET_PENDING=5
TOPIC_SEEDS=american candy,sour lollies,vegan candy,halal candy
```

Meaning:
- `TOPIC_GENERATION_SOURCE=auto`: prefer GSC opportunities, then fall back to seed topics.
- `TOPIC_GENERATION_SOURCE=seed`: generate only from `TOPIC_SEEDS`.
- `TOPIC_GENERATION_SOURCE=gsc`: generate only from Google Search Console opportunity data.
- `TOPIC_TARGET_PENDING=5`: try to keep at least 5 pending topics in `topics.csv`.
- `TOPIC_SEEDS`: seed topics used when seed generation is enabled.

### 4. Run The Program

#### Process the current `topics.csv` in batch mode

```bash
.venv/bin/python src/run_mvp.py --mode batch
```

#### Create only 1 draft per day

```bash
SEO_RUN_MODE=daily DAILY_LIMIT=1 .venv/bin/python src/run_mvp.py --mode daily
```

#### Replenish topics automatically during the daily run

```bash
AUTO_GENERATE_TOPICS=true TOPIC_GENERATION_SOURCE=auto TOPIC_TARGET_PENDING=5 TOPIC_SEEDS="american candy,sour lollies,vegan candy" SEO_RUN_MODE=daily DAILY_LIMIT=1 .venv/bin/python src/run_mvp.py --mode daily --generate-topics
```

#### Publish immediately after creation

```bash
AUTO_PUBLISH_CREATED_POSTS=true AUTO_GENERATE_TOPICS=true SEO_RUN_MODE=daily DAILY_LIMIT=1 .venv/bin/python src/run_mvp.py --mode daily --generate-topics --publish-created
```

The Python workflow now does all of the following:
- reads `topics.csv`
- tracks local run state to avoid re-processing the same row
- dedupes against WordPress slugs and titles before creating a post
- optionally uses OpenAI for article generation
- optionally uses GSC keywords and top pages for SEO enrichment
- builds structured SEO HTML with excerpt, FAQ, and internal links
- sends a Telegram summary

### 5. Schedule Daily Runs On macOS With launchd

New scripts in this repo:
- `scripts/run_daily_seo.sh`: actual daily runner
- `scripts/install_launchd.sh`: installs the launchd job
- `scripts/uninstall_launchd.sh`: removes the launchd job

#### Install a job that runs every day at 09:15

```bash
cd ~/agents/agents/sweetsworld-seo-agent
bash scripts/install_launchd.sh 9 15
```

This creates:
- `~/Library/LaunchAgents/com.sweetsworld.seo-agent.daily.plist`

Check status:

```bash
launchctl list | grep com.sweetsworld.seo-agent.daily
```

Watch logs:

```bash
tail -f logs/daily-seo.log
```

Remove the scheduled job:

```bash
bash scripts/uninstall_launchd.sh
```

### Success Criteria

You should see all of the following when the workflow is healthy:

1. New WordPress drafts appear, or published posts if `AUTO_PUBLISH_CREATED_POSTS=true` is enabled.
2. `data/seo_daily_state.json` records the latest run state.
3. `topics.csv` grows with unique rows when automatic topic generation is enabled.
4. Telegram receives a summary with created links or error details.

## Troubleshooting

### 401 Unauthorized

Cause: WordPress authentication failed.

Fix:
- Check `WP_USERNAME`.
- Check `WP_APP_PASSWORD` and keep the spaces.
- Confirm the Application Password still exists.
- Confirm the user can create posts.

### 403 Forbidden

Cause: insufficient permissions or REST API access is blocked.

Fix:
- Confirm the user role is Editor or Administrator.
- Confirm the WordPress REST API is enabled.
- Check whether security plugins are blocking the request.

### 404 Not Found

Cause: the WordPress REST API endpoint is unavailable.

Fix:
- Verify `WP_BASE_URL`.
- Test `https://sweetsworld.com.au/wp-json/wp/v2/posts` directly.
- Re-save WordPress permalink settings.

### No new rows are added to `topics.csv`

Cause: the generated suggestions duplicate existing rows, or OpenAI / GSC data is unavailable.

Fix:
- Change `TOPIC_SEEDS` to more specific topic areas.
- Verify `OPENAI_API_KEY`.
- If using GSC, set `USE_GSC_DATA=true` and confirm the service account works.

### launchd does not trigger

Cause: the launchd job was not loaded, or the plist was removed.

Fix:
- Run `launchctl list | grep com.sweetsworld.seo-agent.daily`.
- Inspect `logs/launchd.stdout.log` and `logs/launchd.stderr.log`.
- Re-run `bash scripts/install_launchd.sh 9 15`.

## Feature Checklist

### Implemented
- WordPress REST API integration
- Draft creation with optional immediate publish
- Template-based article generation
- OpenAI-based article generation
- Google Search Console enrichment
- Telegram notifications
- CSV batch processing
- Local run-state tracking
- WordPress slug/title dedupe
- Automatic `topics.csv` replenishment
- macOS launchd install/uninstall scripts

### Future Work
- Pull WooCommerce product data into articles
- Auto-set featured images
- Auto-assign categories and tags
- Add content quality scoring
- Update existing posts in batches
- Run content A/B tests
## Development Environment

- Python 3.10+
- VS Code (recommended)
- Git

## License

MIT

## Contact

Please use GitHub Issues for questions or bug reports.
