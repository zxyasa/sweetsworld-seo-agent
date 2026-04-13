# Lessons Learned

## CSS / Flexbox Layout

- **Rule**: 在 Flexbox 布局中做 sticky 侧边栏，必须用纯 CSS `position:sticky`，禁止用 jQuery `position:relative + align-self:flex-start` 方案
- **Context**: newcastlehub 侧边栏连续失败 5 次。根本原因：设置 `align-self:flex-start` 让 `.post-sidebar` 收缩到侧边栏自然高度；`position:relative; top:Xpx` 的偏移超出父容器，被 overflow clipping 裁掉，用户看不到任何效果
- **Prevention**: 遇到"sticky 没效果"时，第一步检查父容器高度和 overflow 属性，而不是调整 JS 计算逻辑。正确方案：父容器保持 `align-self:stretch`（默认），`#secondary { position:sticky; top:90px }` 即可
- **Counter**: 5
