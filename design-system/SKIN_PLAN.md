# SweetsWorld 皮肤计划

## 当前配色体系（Default Skin）

### Flatsome 主题级（全站生效）
| 角色 | 颜色 | CSS 变量 | 用途 |
|------|------|---------|------|
| Primary | `#2596be` | `--primary-color` | 导航链接、购物车图标、主按钮（.button.primary） |
| Secondary | `#C05530` | `--fs-color-secondary` | 辅助强调 |
| Alert | `#dc0f67` | `--fs-color-alert` | .button.alert 按钮底色 |
| Success | `#627D47` | `--fs-color-success` | 成功状态 |
| Base text | `#4a4a4a` | `--fs-color-base` | 正文字体 |
| Link | `#334862` | `--fs-experimental-link-color` | 正文链接 |
| Font | Lato | — | 全站字体 |

### 首页区块级（Code Snippet + 页面 HTML）
| 角色 | 颜色 | 位置 |
|------|------|------|
| Top bar 背景 | `#ee5a24` | Snippet 15 |
| Top bar 文字 | `#ffffff` | Snippet 15 |
| Coupon 码背景 | `#ffffff` on `#ee5a24` | Top bar + Newsletter |
| Newsletter 渐变 | `rgb(254,224,110)` → `rgb(255,213,215)` | UX Block 72001 |
| Subscribe 按钮 | `#ee5a24` | UX Block 72001 |
| Section 黄 | `rgb(254, 224, 110)` | We Make It Easy / New Arrivals |
| Section 粉 | `rgb(255, 213, 215)` | Great Prices / Reviews |
| Section 青 | `rgb(193, 227, 228)` | Twizzlers / Gifts |
| Section 橙粉 | `rgb(255, 214, 199)` | Hot Sauce |
| Section 暖黄 | `rgb(254, 227, 125)` | Reviews card |
| 正文标题 | `#3b4b5c` | H2/H3 |
| 正文段落 | `rgb(66, 66, 66)` / `#555` | Body text |
| 次要文字 | `rgb(119, 119, 119)` / `#888` | Subtitle |
| 社交证明强调 | `#ee5a24` | Snippet 21 产品名 |

### SEO Agent 博客级（content_generator.py skin tokens）
| Token | 值 | 用途 |
|-------|------|------|
| `color_primary` | `#6bb6d9` | 博客内链接、价格高亮 |
| `color_primary_dark` | `#7aa9c2` | "You may also want to buy" 标签 |
| `color_text_primary` | `#3b4b5c` | 博客正文 |
| `color_cta_accent` | `#ff6b6b` | CTA 按钮 |
| `color_card_bg` | `#ffffff` | 产品卡片背景 |
| `color_gallery_bg` | `#f8fbfd` | 产品区块背景 |

---

## 可换肤元素清单

### 高影响（用户一眼看到的）
| # | 元素 | 当前 | 换肤方式 | 难度 |
|---|------|------|---------|------|
| 1 | **Top bar 背景** | `#ee5a24` | Snippet 15 修改 | 低 |
| 2 | **Top bar 文案** | "New here? Use code SWEET10..." | Snippet 15 修改 | 低 |
| 3 | **Newsletter 渐变背景** | 黄→粉 | UX Block 72001 修改 | 低 |
| 4 | **首页 Hero 图片** | home-banner-image.jpg | WP Media + 页面 HTML | 中 |
| 5 | **Section 背景色** (×5) | 黄/粉/青/橙粉/暖黄 | 页面 HTML inline style | 中 |
| 6 | **Button alert 底色** | `#dc0f67` (Flatsome) / `#ee5a24` (我们的) | Flatsome Customizer 或 CSS | 中 |
| 7 | **社交证明弹窗强调色** | `#ee5a24` | Snippet 21 修改 | 低 |

### 中影响（浏览时看到的）
| # | 元素 | 当前 | 换肤方式 | 难度 |
|---|------|------|---------|------|
| 8 | **博客产品卡片颜色** | `#6bb6d9` / `#f8fbfd` | skin token 文件 | 低 |
| 9 | **Reviews 卡片背景** (×3) | 粉/青/暖黄 | 页面 HTML | 中 |
| 10 | **Brand slider 分页点** | `#bfe9ec` | 页面 HTML CSS | 低 |
| 11 | **Category 图标** (×5) | SVG 单色 | 替换 SVG 文件 | 高 |
| 12 | **USP slider 图片** (×4) | 固定 PNG | 替换媒体文件 | 中 |

### 低影响（底层/全站）
| # | 元素 | 当前 | 换肤方式 | 难度 |
|---|------|------|---------|------|
| 13 | **Flatsome Primary** | `#2596be` | Customizer → Colors | 低但全站影响 |
| 14 | **Flatsome Alert** | `#dc0f67` | Customizer → Colors | 低但全站影响 |
| 15 | **Footer 背景** | 默认 | Customizer → Footer | 低 |
| 16 | **Font** | Lato | Customizer → Typography | 低但全站影响 |

---

## 季节性皮肤方案

### 🎄 Christmas (11月-12月)
| 元素 | Default → Christmas |
|------|-------------------|
| Top bar 背景 | `#ee5a24` → `#c0392b`（深红） |
| Top bar 文案 | "SWEET10" → "XMAS15 — 15% off Christmas gifts" |
| Section 背景 | 黄/粉/青 → 红/绿/金 `rgb(192,57,43)` / `rgb(39,174,96)` / `rgb(241,196,15)` |
| Newsletter 渐变 | 黄→粉 → 红→金 |
| Hero 图片 | 换成圣诞主题 banner |
| 博客 skin | `color_primary: #c0392b`, `color_cta_accent: #27ae60` |

### 🐣 Easter (3月-4月)
| 元素 | Default → Easter |
|------|----------------|
| Top bar 背景 | `#ee5a24` → `#8e44ad`（紫色） |
| Section 背景 | → 淡紫/淡黄/淡绿 `rgb(232,218,239)` / `rgb(254,249,195)` / `rgb(212,239,223)` |
| Newsletter 渐变 | → 紫→黄 |
| Hero 图片 | Easter eggs 主题 |

### 🎃 Halloween (10月)
| 元素 | Default → Halloween |
|------|-------------------|
| Top bar 背景 | `#ee5a24` → `#2c3e50`（深色） |
| Section 背景 | → 橙/黑/紫 `rgb(243,156,18)` / `rgb(44,62,80)` / `rgb(142,68,173)` |
| 博客 skin | `color_primary: #e67e22`, `color_cta_accent: #8e44ad` |

### 💝 Valentine's Day (2月)
| 元素 | Default → Valentine |
|------|-------------------|
| Top bar 背景 | `#ee5a24` → `#e74c3c` |
| Section 背景 | → 粉红/玫瑰/白 |
| Newsletter 渐变 | → 粉→红 |

### 🇦🇺 Australia Day (1月)
| 元素 | Default → Australia Day |
|------|----------------------|
| Top bar | `#ee5a24` → `#003580`（深蓝） |
| Section 背景 | → 蓝/金/绿 |

---

## 实施方式

### 自动换肤流程
1. `site.json` 的 `active_skin` + `skin_valid_from` / `skin_valid_until` 控制当前激活的皮肤
2. SEO agent 博客颜色：`design-system/skins/{skin_name}.md` token 文件
3. 首页颜色：通过 Code Snippet 读取当前 skin 配置，动态输出 CSS override
4. Top bar 文案/颜色：Snippet 15 改为从 skin 配置读取
5. Newsletter 颜色：UX Block 72001 改为用 CSS 变量，通过 snippet 注入变量值

### 换肤 Snippet 架构（建议）
```php
// 一个主 snippet 读取 skin 配置，注入 CSS 变量
add_action('wp_head', function() {
    $skin = get_option('sw_active_skin', 'default');
    $colors = sw_get_skin_colors($skin);
    echo "<style>:root {";
    foreach ($colors as $name => $value) {
        echo "--sw-{$name}: {$value};";
    }
    echo "}</style>";
});
```

然后所有 Code Snippet 和 UX Block 里的硬编码颜色改为 `var(--sw-topbar-bg)` 等 CSS 变量。

### 不换的（保持固定）
- Logo
- Font（Lato）
- 页面结构/布局
- Category 图标形状
- 产品卡片结构
