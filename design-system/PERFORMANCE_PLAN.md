# SweetsWorld 首页性能优化计划

## 当前状况（2026-04-11）
- **Mobile**: Score 40, LCP 28.2s, TBT 1,490ms
- **Desktop**: Score 39, LCP 5.5s, TBT 1,040ms
- **页面总重**: 3.2MB+（top 15 资源）
- **JS 文件**: 40+ 个

## 根因分析

### P0: reCAPTCHA 重复加载（2.2MB，占 67%）
- reCAPTCHA Enterprise（Snippet 14）+ reCAPTCHA v3（Contact Form 7）+ Wordfence login security 各自加载一份
- 结果：**4 个 recaptcha script 标签**，Lighthouse 看到 6 个实例（363KB × 6 = 2.2MB）
- **首页不需要 reCAPTCHA**——只有 login/register/contact 页面需要
- **修法**: Snippet 14 加 `if (is_page('contact') || is_account_page())` 条件；CF7 recaptcha 限制到 contact 页

### P1: Google Pay JS（391KB）
- `pay.google.com/gp/p/js/pay.js` 在首页加载
- 首页没有购买按钮，不需要 Google Pay
- **修法**: Stripe 插件设置里限制 Google Pay JS 只在 cart/checkout 加载

### P2: 未使用的 JS（1,631KB 可节省）
- 主要是 reCAPTCHA（P0 修了就好）
- 其次是 Stripe/PayPal 的 JS
- **修法**: 各插件设置 → 限制加载页面

### P3: Swiper CDN（137KB）
- 我们新加的 slider 库
- 已加 `defer`，但还是额外的下载
- **修法**: 自托管 Swiper（上传到 WP media），减少 DNS lookup；或用 WP Rocket 的 CDN 缓存

### P4: 第三方脚本
| 脚本 | 大小 | 首页需要？ |
|------|------|-----------|
| reCAPTCHA × 4 | 2.2MB | ❌ 不需要 |
| Google Pay | 391KB | ❌ 不需要 |
| FontAwesome (Snippet 5) | ~100KB | ⚠️ 看是否有用到图标 |
| WonderPush | ~50KB | ⚠️ 确认是否在用 |
| Pinterest pinit.js | ~30KB | ⚠️ 首页没有 Pin 按钮 |
| TikTok ajaxSnippet.js | ~20KB | ✅ tracking pixel |
| Facebook pixel | ~20KB | ✅ tracking pixel |
| Klaviyo | ~30KB | ✅ newsletter 需要 |
| GTM/Google Ads | ~80KB | ✅ analytics 需要 |
| Trustpilot | ~20KB | ✅ reviews |
| Stripe JS | ~100KB | ⚠️ mini cart 可能需要 |
| PayPal JS | ~100KB | ⚠️ mini cart 可能需要 |

## 优化步骤（按影响排序）

### Step 1: reCAPTCHA 限制加载页面（预计节省 2MB+）
- 修改 Snippet 14：只在 login/register/contact 页加载 reCAPTCHA Enterprise
- CF7 设置：recaptcha 只在 contact 页启用
- Wordfence：login security recaptcha 已限制在 login 页
- **预期效果**: LCP 大幅改善，Score 可能翻倍

### Step 2: Google Pay 限制到 cart/checkout（预计节省 391KB）
- WP Admin → WooCommerce → Settings → Payments → Stripe → Google Pay → 勾选"Only load on cart and checkout"
- 或通过 Code Snippet dequeue

### Step 3: WonderPush 评估（预计节省 50KB）
- 确认是否在用浏览器推送通知
- 如果不用 → 停用插件

### Step 4: FontAwesome 评估（预计节省 100KB）
- Snippet 5 加载 FontAwesome kit
- 检查首页是否有 FA 图标
- 如果没有 → 限制到需要的页面

### Step 5: Swiper 自托管（减少 DNS lookup）
- 下载 swiper-bundle.min.js + .css 到 WP media
- Snippet 17 改为从本地加载
- WP Rocket 会自动缓存本地文件

### Step 6: WP Rocket 优化配置
- 确认"延迟 JavaScript 执行"已开启
- 确认"CSS 文件优化"已开启
- 确认 CDN 配置正确
- 预加载关键资源（hero 图片）

## 预期效果
| 步骤 | 节省 | 累计预期 Score |
|------|------|---------------|
| 现状 | — | 40 |
| Step 1 (reCAPTCHA) | ~2.2MB | 60-70 |
| Step 2 (Google Pay) | ~391KB | 70-75 |
| Step 3-4 (WonderPush + FA) | ~150KB | 75-80 |
| Step 5-6 (Swiper + WP Rocket) | DNS + cache | 80+ |
