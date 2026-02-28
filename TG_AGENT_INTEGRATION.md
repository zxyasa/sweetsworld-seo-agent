# Telegram Bot (tg_agent) 集成指南

## 概述

通过 Telegram bot 调用 sweetsworld-seo-agent，无需手动运行脚本。

## 支持的操作

- `seo_create` — 创建单篇 SEO 文章
- `seo_batch` — 批量生成 topics.csv 中的所有文章
- `seo_status` — 查看 SEO agent 配置状态
- `seo_logs` — 查看最近的生成日志

---

## 🔧 配置步骤

### 1. 更新 `project_profiles.py`

在 `/Users/michaelzhao/agents/agents/tg_agent/project_profiles.py` 中添加 sweetsworld 配置：

```python
PROJECTS: Dict[str, ProjectProfile] = {
    "stock1": ProjectProfile(
        name="stock1",
        aliases=("stock1", "stock_reporter"),
        repo_dir=Path("~/agents/stock1").expanduser().resolve(),
        entrypoint="main.py",
        venv_dir=".venv",
        output_log="stock1.out",
        ps_grep_expr="[s]tock1.*python|[s]tock1.*main",
        pkill_expr="stock1.*python",
    ),
    "sweetsworld": ProjectProfile(
        name="sweetsworld",
        aliases=("sweetsworld", "seo", "seo_agent"),
        repo_dir=Path("~/agents/sweetsworld-seo-agent").expanduser().resolve(),
        entrypoint="src/run_mvp.py",
        venv_dir=".venv",
        output_log="seo.out",
        ps_grep_expr="[s]weetsworld.*python|seo.*python",
        pkill_expr="sweetsworld.*python",
    )
}
```

### 2. 更新 `allowlist.yaml`

在 `/Users/michaelzhao/agents/agents/tg_agent/allowlist.yaml` 中添加：

```yaml
# 允许的动作
actions:
  - status
  - tail_log
  - git_pull
  - restart_tmux
  - stop_tmux
  - start_tmux
  - pip_install
  - ps_check
  - web_search
  - stock1_status
  - stock1_start
  - stock1_stop
  - stock1_logs
  - seo_create      # 新增
  - seo_batch       # 新增
  - seo_status      # 新增
  - seo_logs        # 新增

# 需要二次确认的敏感操作
confirm_required:
  - restart_tmux
  - stop_tmux
  - git_pull
  - pip_install
  - stock1_start
  - stock1_stop
  - seo_create      # 新增
  - seo_batch       # 新增
```

### 3. 更新 `executor.py`

在 `/Users/michaelzhao/agents/agents/tg_agent/executor.py` 的最后，`return f"❌ 未实现的动作: {action}"` 之前添加：

```python
    elif action == "seo_create":
        """创建单篇 SEO 文章"""
        import sys
        sys.path.insert(0, str(BASE / "sweetsworld-seo-agent" / "src"))

        try:
            from autogen_integration import create_seo_article

            title = params.get("title", "")
            slug = params.get("slug", "")
            keyword = params.get("primary_keyword", "")
            category = params.get("category_hint", "Products")

            if not title or not slug or not keyword:
                return "❌ 缺少必需参数: title, slug, primary_keyword"

            result = create_seo_article(
                title=title,
                slug=slug,
                primary_keyword=keyword,
                category_hint=category,
                use_ai=True,
                use_gsc=True
            )

            if result["status"] == "success":
                return f"✅ SEO 文章已创建！\n📝 标题: {title}\n🔗 链接: {result['post_link']}\n📊 模式: {result['mode']}\n📏 字数: {result['characters']} 字符"
            else:
                return f"❌ 创建失败: {result['message']}"

        except Exception as e:
            return f"❌ SEO 创建失败: {str(e)}"

    elif action == "seo_batch":
        """批量创建 SEO 文章（从 topics.csv）"""
        profile = get_project("sweetsworld")
        if not profile:
            return "❌ sweetsworld 配置不存在"

        activate = f"source {shlex.quote(profile.venv_dir)}/bin/activate && " if profile.venv_dir else ""
        cmd = (
            f"cd {shlex.quote(str(profile.repo_dir))} && "
            f"{activate}python {shlex.quote(profile.entrypoint)}"
        )
        return _run(cmd, timeout=300)  # SEO 生成可能需要更长时间

    elif action == "seo_status":
        """查看 sweetsworld SEO agent 状态"""
        profile = get_project("sweetsworld")
        if not profile:
            return "❌ sweetsworld 配置不存在"

        topics_csv = profile.repo_dir / "topics.csv"
        env_file = profile.repo_dir / ".env"

        status_parts = []
        status_parts.append(f"📁 项目路径: {profile.repo_dir}")
        status_parts.append(f"🔧 .env 配置: {'✅ 存在' if env_file.exists() else '❌ 缺失'}")
        status_parts.append(f"📋 topics.csv: {'✅ 存在' if topics_csv.exists() else '❌ 缺失'}")

        if topics_csv.exists():
            lines = _run(f"wc -l {shlex.quote(str(topics_csv))}")
            status_parts.append(f"📝 Topics 数量: {lines}")

        return "\n".join(status_parts)

    elif action == "seo_logs":
        """查看 SEO agent 最近的日志"""
        profile = get_project("sweetsworld")
        if not profile:
            return "❌ sweetsworld 配置不存在"

        log_path = _safe_path(str(profile.output_log_path()))
        if not log_path.exists():
            return "❌ 日志文件不存在（还没有运行过 seo_batch）"

        return _run(f"tail -n 100 {shlex.quote(str(log_path))}")
```

---

## 📱 使用示例

### 示例 1：批量生成文章

```
你：批量生成 SEO 文章
Bot 规划：
  1. seo_batch — 运行批量生成
  2. seo_logs — 查看生成日志
结果：Bot 批量创建所有 topics.csv 中的文章
```

### 示例 2：创建单篇文章

```
你：创建一篇关于 Australian Chocolate 的文章
Bot 规划：
  1. seo_create — 创建单篇文章
     参数：
       - title: "Ultimate Guide to Australian Chocolate 2026"
       - slug: "australian-chocolate-guide-2026"
       - primary_keyword: "australian chocolate"
       - category_hint: "Chocolate"
结果：Bot 生成并发布到 WordPress
```

### 示例 3：查看状态

```
你：SEO agent 状态怎么样
Bot 规划：
  1. seo_status — 查看配置状态
结果：显示配置文件、topics.csv 是否存在
```

### 示例 4：查看日志

```
你：看看最近的 SEO 生成日志
Bot 规划：
  1. seo_logs — 查看日志
```

---

## 🎯 工作流程

### 批量生成文章

```bash
# Telegram bot 会自动执行：
cd ~/agents/sweetsworld-seo-agent
source .venv/bin/activate
python src/run_mvp.py
```

输出日志保存到 `seo.out`

### 单篇文章创建

```python
# Telegram bot 会调用 autogen_integration.py:
result = create_seo_article(
    title="...",
    slug="...",
    primary_keyword="...",
    category_hint="...",
    use_ai=True,
    use_gsc=True
)
```

---

## ⚠️ 注意事项

1. **确认机制**：`seo_create` 和 `seo_batch` 需要二次确认（避免误操作）
2. **超时设置**：`seo_batch` 的超时设置为 300 秒（5 分钟），适应 AI 生成的长时间运行
3. **依赖环境**：确保 sweetsworld-seo-agent 的虚拟环境已安装所有依赖

---

## 🔄 vs AutoGen 集成

| 特性 | tg_agent | AutoGen |
|------|----------|---------|
| **触发方式** | Telegram 消息 | Python 代码调用 |
| **适用场景** | 日常快捷操作 | 复杂多步骤工作流 |
| **确认机制** | Telegram 按钮确认 | 代码逻辑控制 |
| **通知方式** | Telegram 消息 | 程序返回值 |

**建议使用方式：**
- **日常使用**：用 tg_agent（在手机/电脑上发 Telegram 消息即可）
- **自动化流程**：用 AutoGen（多 agent 协作、定时任务等）

---

## 🚀 快速开始

1. 按照上面的步骤更新 3 个文件：
   - `project_profiles.py`
   - `allowlist.yaml`
   - `executor.py`

2. 重启 Telegram bot：
   ```bash
   cd ~/agents/tg_agent
   pkill -f "tg_agent.*python" || pkill -f "bot.py"
   source .venv/bin/activate
   nohup python bot.py > bot.stdout.log 2> bot.stderr.log &
   ```

3. 在 Telegram 中测试：
   - 发送："SEO agent 状态"
   - 发送："批量生成 SEO 文章"
   - 发送："创建一篇关于巧克力的文章"

---

## 📝 配置检查清单

- [ ] 已更新 `project_profiles.py` 添加 sweetsworld 配置
- [ ] 已更新 `allowlist.yaml` 添加 4 个 seo actions
- [ ] 已更新 `executor.py` 添加 4 个 action handlers
- [ ] sweetsworld-seo-agent 的 `.env` 文件已配置
- [ ] sweetsworld-seo-agent 的虚拟环境已安装依赖
- [ ] Telegram bot 已重启
- [ ] 已在 Telegram 中测试 `seo_status`

---

## 故障排除

### 问题：seo_create 报错 "❌ 缺少必需参数"
**原因：** LLM 规划时没有提供完整的参数

**解决：** 在 Telegram 中更明确地说明文章信息，例如：
```
创建一篇文章：
- 标题：Ultimate Guide to Australian Chocolate 2026
- 关键词：australian chocolate
- 分类：Chocolate
```

### 问题：seo_batch 超时
**原因：** AI 生成需要较长时间

**解决：**
1. 检查 topics.csv 中的条目数量（建议一次不超过 5 篇）
2. 增加 executor.py 中的 timeout 参数
3. 查看日志确认进度：`seo_logs`

### 问题：找不到 autogen_integration 模块
**原因：** Python 路径问题

**解决：**
确保 executor.py 中的路径正确：
```python
sys.path.insert(0, str(BASE / "sweetsworld-seo-agent" / "src"))
```

---

## 更新记录

- **2026-02-12** — 初始版本，支持 4 个 seo actions
