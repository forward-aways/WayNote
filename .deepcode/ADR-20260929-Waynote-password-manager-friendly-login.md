# ADR-20260929：登录表单适配浏览器密码管理器

- 状态：已完成（Edge 实测确认：首次登录可触发保存提示）
- 日期：2026-09-29
- 触发：用户反馈「输入账号密码后浏览器不弹保存提示」，并询问是否与缓存/Cookie 有关
- 范围：登录/注册页的表单提交语义与规范属性；登录后的跳转方式
- 不包含：Cookie 会话改造（继续使用 localStorage + Bearer）、邮件验证码登录（独立路线）

---

## 1. 取证与结论

**用户假设（缓存/Cookie）不成立**：浏览器"保存密码"是密码管理器（Chrome/Edge 内置或扩展）的独立机制，与 HTTP 缓存、Cookie 无关。

| 检查项 | 结果 | 证据 |
|---|---|---|
| Cookie | 未使用（JWT 存 localStorage） | `stores/auth.ts`、`api/http.ts` |
| Service Worker | 未使用 | 全量扫描无 `serviceWorker` |
| 表单原生提交 | **从未发生**：按钮非 submit 类型，`@submit.prevent` 永不被触发 | `LoginView.vue` 旧代码无 `native-type`；输入框用 `@keyup.enter` 代替 |
| 登录成功信号 | SPA 路由切换（`router.push`），无页面导航 | 旧代码 |
| 规范属性 | `autocomplete="email"`（应为 `username`）；无 `name` | 旧代码 |

**根因**：密码管理器依赖「密码框 + 表单提交事件 + 登录成功信号（导航/页面替换）」三要素，而我们的 SPA 登录流程三要素几乎全缺。

## 2. 方案与实现

1. **原生提交语义**：登录/注册按钮 `native-type="submit"`，由表单 `@submit.prevent` 统一接管；**同步移除**按钮 `@click` 与密码框 `@keyup.enter`，否则原生提交 + JS 回调会双重触发登录请求。
2. **规范属性**：登录邮箱 `autocomplete="username"` + `name="username"`；密码 `name="password"`（登录 `current-password` / 注册 `new-password`）；注册页补充 `name`。
3. **整页跳转**：登录/注册成功后 `window.location.assign('/trips')` 替代 `router.push`——给密码管理器最强的成功信号，并彻底重置内存状态。

**前置依赖已实测验证**：
- `el-form` 未禁用属性透传（源码无 `inheritAttrs`）→ Vue 默认将 `@submit` 合并到根 `<form>` 元素；
- `el-button` 存在 `nativeType` prop（`button|submit|reset`）；
- `el-input` 的 `name`/`autocomplete` 为**正式 prop**，且渲染真实 `<input>` 时通过 `mergeProps(base, attrs, { name: props.name, autocomplete: props.autocomplete })` 明确落地。

## 3. 取舍与反例

- **代价**：整页跳转多一次 JS 解析执行（数百毫秒）并失去路由过渡动画；换来最高识别率（用户已知悉并接受）。属一行改动，随时可撤。
- **反例/边界**：
  1. Safari/Firefox 对 XHR 登录更挑剔，行为可能仍与 Chrome 不同；
  2. `chrome://settings/passwords` 中的「从不保存」记录会屏蔽提示（需先删除该条）；
  3. 扩展型密码管理器（1Password/Bitwarden）会接管原生提示，属其自身策略；
  4. 因此**无法 100% 保证**任何浏览器的提示行为，本方案只是消除应用侧的全部阻碍因素。

## 4. 测试与验收

| ID | 内容 | 结果 |
|---|---|---|
| P1 | type-check / lint / build | 通过 |
| P2 | 无双触发残留（无 `@click="onSubmit"` / `@keyup.enter`） | 通过（grep 断言） |
| P3 | 浏览器实测：登录后是否弹出保存提示（Edge） | **通过**（清除站点数据后首次登录成功触发） |
| P4 | 回归：登录/注册/退出流程可用 | 通过 |

### 4.1 实测中的两个干扰因素（复盘，重要）

用户首次实测"不弹"，清除浏览器数据后"弹了"。复盘确认**与 Cookie 无关**（应用不使用 Cookie），真实原因是两个干扰因素：

1. **登录态遮蔽**：JWT 存 localStorage 且 7 天有效；未退出登录时访问 `/login` 会被路由守卫重定向到 `/trips`，**登录表单根本不会出现**，自然无法触发保存提示。清除"Cookie 和其他站点数据"实际清掉了 localStorage（= 强制登出）与浏览器自动填充状态，所以"突然就弹了"。
2. **一次性提示**：密码一旦被保存，Edge/Chrome 后续登录只做静默自动填充、不再重复提示。"第二次不弹"是预期行为；要复现提示需先在 `edge://settings/passwords` 删除已保存条目。

### 4.2 若仍不弹的排查顺序（本次未走到，留档）

`edge://settings/passwords` 开关与"从不保存"列表 → `edge://policy` 搜 `PasswordManagerEnabled`（企业策略可能禁用）→ 新建干净浏览器配置文件 → **最小复现页对照实验**（原生 POST → 303 → GET，可一刀切开"环境问题"与"代码问题"）。

若 P3 仍失败：排查 never-saved 列表与扩展干扰；长期方向为邮件验证码登录（从根上绕开密码管理）。

## 5. 最终结果（Phase 5）

- 变更文件：`LoginView.vue`、`RegisterView.vue`（提交语义 + 规范属性 + 整页跳转 + 清理未用的 `useRouter`）。
- 验证结果：Edge 实测通过——清除站点数据后首次登录即触发保存提示；"第二次不弹/不用再登录"均为预期行为（已保存条目 + JWT 会话）。
- 经验：SPA 的"零原生提交 + 零导航"会让密码管理器完全失去判断依据；把表单语义还原成浏览器期望的形态，成本极低但收益明确。