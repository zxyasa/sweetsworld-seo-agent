# Newcastle Hub — 网站改进计划

> 站点: newcastlehub.info
> 皮肤工具: `apps/wordpress-ai-ops/scripts/apply_skin.py`
> 最后更新: 2026-04-08

---

## 全站页面 & 链接总图

### 现有页面清单（已发布）

| 类别 | 页面 | URL | 备注 |
|------|------|-----|------|
| **首页** | Home 2 | `/` (page 403) | 实际首页 |
| **服务总览** | Services | `/services/` | 入口页，需内链完善 |
| **网站建设** | Website Service | `/website-service/` | |
| **营销/SEO** | Marketing Service | `/marketing-service/` | |
| | Google Business 优化 | `/google-business-optimisation-newcastle/` | |
| | Google Business（餐饮）| `/google-business-profile-for-restaurants-newcastle/` | |
| | Facebook 设置（餐饮）| `/facebook-page-setup-for-restaurants-newcastle/` | |
| **POS & 系统** | POS Setup | `/pos-setup-newcastle/` | |
| | 网上点餐 | `/online-ordering-newcastle/` | |
| | QR 桌台点餐 | `/qr-table-ordering-newcastle/` | |
| | 预约系统 | `/booking-system-newcastle/` | |
| | 电商建站 | `/ecommerce-setup-newcastle/` | |
| | 餐厅 Square 全套 | `/newcastle-restaurant-square-setup/` | |
| **托管** | Hosting Plan | `/hosting-plan/` | |
| | Starter+ | `/web-hosting-starter/` | |
| | Freedom+ | `/web-hosting-freedom/` | |
| | Premier+ | `/web-hosting-premier/` | |
| **AI** | AI Service | `/ai-service/` | |
| | AI Implementation Pack | `/ai-service-implementation-pack/` | |
| **行业解决方案** | 餐厅/咖啡 | `/restaurant-solutions/` | 需加 Case Study 内链 |
| | 零售 | `/retail-solutions/` | 需加 Case Study 内链 |
| | 汽修/机械 | `/mechanic-solutions/` | |
| | 美发/美容 | `/beauty-salon-solutions/` | |
| | 建筑/工程 | `/trades-solutions/` | 需加 Case Study 内链 |
| **信任页面** | About | `/about/` | |
| | Why Choose Us | `/why-choose-newcastle-hub/` | |
| | Portfolio | `/portfolio/` | |
| | Free Audit（CTA）| `/free-newcastle-business-audit/` | 核心转化入口 |
| | **Testimonials** | `/testimonials/` | ⚠️ ID 973，AI 初稿，需真实评价 |
| **案例研究** | 零售→电商 | `/case-study-retail-ecommerce/` | ⚠️ ID 969，AI 初稿 |
| | 餐饮 | `/case-study-restaurant/` | ⚠️ ID 970，AI 初稿 |
| | 专业服务（会计/律所）| `/case-study-professional-services/` | ⚠️ ID 971，AI 初稿 |
| | Tradesman | `/case-study-trades/` | ⚠️ ID 972，AI 初稿 |
| **法律页面** | Privacy Policy | `/privacy-policy/` | ⚠️ 草稿，内容是 WP 占位模板，需重写 |
| | Terms & Conditions | `/terms-and-conditions/` | ❌ 不存在，需新建 |
| **其他** | Blog | `/blog/` | |
| | Contact | `/contact/` | |

---

## 待办事项

### 🔴 P1 — Case Studies 替换真实数据

**背景**：4 个 Case Study 页面已发布，内容为 AI 占位初稿。上线推广前必须替换真实数据。

| 页面 | 需替换内容 | 占位数字（待核实）|
|------|-----------|-----------------|
| `/case-study-retail-ecommerce/` | 客户背景、成果数字、客户评价 | 35% 收入来自线上，$4,800/月 |
| `/case-study-restaurant/` | 同上 | 省 $1,200/月佣金，65% 直接下单 |
| `/case-study-professional-services/` | 同上 | 询盘增加 3×，税季满档 |
| `/case-study-trades/` | 同上 | Google Maps 前 3，12 工单/月 |

**行动**：用户提供真实案例细节 → AI 重写对应页面

---

### 🔴 P1 — Testimonials 替换真实评价

- [ ] 替换 4 段占位引用为真实客户原话
- [ ] 嵌入 Google Reviews（需 Google Business Profile Place ID）
- [ ] 更新评分数字（占位：4.8★ / 40+ reviews）

---

### 🟡 P2 — Footer 全面重组

**位置**：ux-blocks ID=450（当前生效的 Footer）

**现有 Bug 清单**（除链接外还有这些问题）：

| 问题 | 位置 | 详情 |
|------|------|------|
| ❌ 服务链接全坏 | Our Services 列 | 5 项全是 `#` 或无链接 |
| ❌ 社交链接全坏 | Col 1 | Facebook/Instagram/Twitter/LinkedIn 全是 `#` |
| ❌ Email href 错误 | Contact 列 | `href="tel:01293123338"` 应为 `mailto:hello@newcastlehub.info` |
| ❌ 地址 href 错误 | Contact 列 | `href="tel:01293123338"` 应为 Google Maps 链接 |
| ❌ 版权名称错误 | 底部 bar | 写的是 "Newcastle IT hub"，应为 "Newcastle Hub" |
| ❌ 无法律链接 | 底部 bar | 没有 Privacy Policy / Terms 链接 |
| ❌ 无公司链接 | 整个 Footer | 没有 About / Portfolio / Case Studies 入口 |

**目标结构（4 列）**：

```
[Logo + 简介 + 社交]  |  [Our Services]           |  [Company]              |  [Contact]
─────────────────────────────────────────────────────────────────────────────────────────
Logo                  |  Website Design →          |  About Us →             |  📞 02 40755307
"Newcastle Hub 帮助   |  /website-service/         |  /about/                |  ✉ hello@newcastlehub.info
本地小企业..."        |                            |                         |  📍 Shop 1089, Stockland
                      |  Digital Marketing →        |  Portfolio →            |     Greenhills, East Maitland
社交图标              |  /marketing-service/        |  /portfolio/            |
                      |                            |                         |
                      |  POS & Systems →           |  Case Studies →         |
                      |  /pos-setup-newcastle/      |  /testimonials/         |
                      |                            |                         |
                      |  Google Business →         |  Why Choose Us →        |
                      |  /google-business-         |  /why-choose-           |
                      |  optimisation-newcastle/   |  newcastle-hub/         |
                      |                            |                         |
                      |  Web Hosting →             |  Free Audit →           |
                      |  /hosting-plan/            |  /free-newcastle-       |
                      |                            |  business-audit/        |
                      |  AI Services →             |                         |
                      |  /ai-service/              |                         |
                      |                            |                         |
                      |  All Services →            |                         |
                      |  /services/                |                         |
─────────────────────────────────────────────────────────────────────────────────────────
© 2026 Newcastle Hub. All Rights Reserved        |  Privacy Policy  |  Terms & Conditions
```

**底部 bar 改动**：
- 版权名从 "Newcastle IT hub" → "Newcastle Hub"
- 右侧加 Privacy Policy + Terms & Conditions 链接

**社交链接**（需确认真实账号 URL）：
- [ ] Facebook URL
- [ ] Instagram URL
- [ ] LinkedIn URL（Twitter/X 可选）

**待确认后执行**

---

### 🟡 P2 — Case Studies → 行业页内链

Case Study 内容确认后，在对应行业页加入内链：

| 来源页面 | 添加链接到 |
|---------|-----------|
| `/restaurant-solutions/` | `/case-study-restaurant/` |
| `/retail-solutions/` | `/case-study-retail-ecommerce/` |
| `/trades-solutions/` | `/case-study-trades/` |
| `/website-service/` | `/case-study-professional-services/` |
| `/marketing-service/` | `/case-study-professional-services/` + `/case-study-trades/` |

---

### 🟡 P2 — Privacy Policy 内容撰写 + 发布

**现状**：ID=3，草稿，内容全是 WordPress 占位模板（"Suggested text:"），没有实际内容。

**需要写的内容**（基于澳洲隐私法 Privacy Act 1988）：
- [ ] 收集的信息类型（姓名、邮件、电话、网站使用数据）
- [ ] 信息用途（联系、提供服务、营销）
- [ ] 第三方共享（Google Analytics、Square、邮件服务商）
- [ ] Cookie 政策
- [ ] 用户权利（查阅、更正、删除）
- [ ] 联系方式（hello@newcastlehub.info）
- [ ] 写完后发布（status: publish）

**行动**：AI 起草 → 用户确认 → 发布

---

### 🟡 P2 — Terms & Conditions 撰写 + 新建

**现状**：页面不存在，需从头创建。

**需要写的内容**：
- [ ] 服务范围（网站建设、营销、POS、托管）
- [ ] 付款条款（定金比例、余款时间）
- [ ] 知识产权（交付后版权归属）
- [ ] 项目变更/追加费用政策
- [ ] 退款政策
- [ ] 服务终止条款（托管取消、数据处理）
- [ ] 免责声明（SEO 效果等不保证具体排名）
- [ ] 适用法律：NSW, Australia

**行动**：AI 起草 → 用户确认 → 创建并发布（slug: `terms-and-conditions`）

---

### 🟢 P3 — Footer 信任区域补充

在 Footer 的 Contact 列或新增一列加入信任链接：

```
Our Work:
  Case Studies  → /testimonials/
  Portfolio     → /portfolio/
  Free Audit    → /free-newcastle-business-audit/
```

---

### 🟢 P3 — 行业解决方案页补全

缺少以下行业的专属页：
- `/accounting-firm-solutions/` — 会计/律所（现在只有 case study）
- `/beauty-salon-solutions/` 已有，但没有对应 case study

---

## 链接关系图

```
首页 (/)
├── /services/                    ← 服务总览
│   ├── /website-service/
│   ├── /marketing-service/
│   ├── /pos-setup-newcastle/
│   ├── /hosting-plan/
│   └── /ai-service/
│
├── 行业解决方案
│   ├── /restaurant-solutions/    → /case-study-restaurant/
│   ├── /retail-solutions/        → /case-study-retail-ecommerce/
│   ├── /trades-solutions/        → /case-study-trades/
│   └── /beauty-salon-solutions/
│
├── 信任页面
│   ├── /testimonials/            ← 汇总入口
│   ├── /case-study-retail-ecommerce/
│   ├── /case-study-restaurant/
│   ├── /case-study-professional-services/
│   ├── /case-study-trades/
│   ├── /portfolio/
│   └── /why-choose-newcastle-hub/
│
├── 转化入口
│   ├── /free-newcastle-business-audit/
│   └── /contact/
│
└── 法律页面（Footer 底部）
    ├── /privacy-policy/        ⚠️ 需重写内容后发布
    └── /terms-and-conditions/  ❌ 需新建
```

---

## 已完成（2026-04-08）

| 任务 | 详情 |
|------|------|
| ✅ Mother's Day 皮肤 | 颜色 + 图片 + CSS + section 背景清除 |
| ✅ Contact 页修复 | 移除背景色，修复图标和按钮颜色 |
| ✅ Recent Projects 画廊 | 移除 masonry 间距 |
| ✅ LiteSpeed 优化 | 8 项缓存设置 |
| ✅ Solution pages \n\n 修复 | 5 个页面字面量换行符修复 |
| ✅ Case Study 初稿 | 4 页 + Testimonials，AI 占位内容已发布 |
| ✅ Footer 全面重组 | ux-blocks/450：4 列结构，修复 7 bug，版权名改正，加法律链接；快照已保存 |
| ✅ Privacy Policy | page ID 3，重写真实内容（澳洲 Privacy Act 1988），已发布；13,229 字符 |
| ✅ Terms & Conditions | 新建 page ID 975，`/terms-and-conditions/`，已发布 |
| ✅ 行业页 → Case Study 内链 | 5 个页面（restaurant/retail/trades/website-service/marketing-service）已加 CTA 内链 |
| ✅ Mobile 修复：AI service 页 | 移除嵌套 HTML 文件结构，改写为 Flatsome shortcode，3 列 span__sm="12" |
| ✅ Mobile 修复：Case Study × 4 | stats grid 加 flex-wrap + @media 100% width，手机下单列堆叠 |

---

## 注意事项

- CSS 注入必须通过 Code Snippets bridge（`/wp/v2/settings` 静默失败）
- `color_replacements` key 不能含双引号
- 皮肤系统详情见 memory: `project_newcastlehub_skin_system.md`
- 背景图规格见 memory: `project_newcastlehub_skin_images.md`
