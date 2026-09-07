# iakes - 《初音未来：缤纷舞台》国服安装包自动追踪与发布

本项目通过 GitHub Actions 定时检测《初音未来：缤纷舞台》（Project SEKAI 国服）**官方官服**与 **Bilibili 服（B服）** 的最新客户端安装包。一旦检测到任一渠道发布新版本，自动下载并将双服 APK 汇总推送至同一 GitHub Release。

## 渠道说明

| 渠道 | 官方入口 | 特征与说明 |
| :--- | :--- | :--- |
| **官服** | [pjsk.nvsgames.cn](https://pjsk.nvsgames.cn) | 朝夕光年发行，支持抖音/手机号登录。官服通过固定跳转短链分发最新 APK。 |
| **Bilibili 服** | [biligame.com/detail/?id=111995](https://www.biligame.com/detail/?id=111995) | 包名 `com.hermes.mk.bilibili`，支持 B 站账号快捷登录（与官服同服游玩）。 |

## 自动化工作流特性

- **轻量检测**：通过 HTTP 头信息与 API 轮询，检测阶段不消耗大额带宽。
- **双服合并发布**：检测到更新后拉取新包，并在同一个 Release 下提供官服与 B 服两份 APK。
- **自动防盗链处理**：内置 Bilibili CDN 防盗链请求头。
- **版本状态记录**：通过 `versions.json` 自动维护最新版本与更新时间。

## 运行方式

- **定时触发**：GitHub Actions 每 2 小时定时轮询一次。
- **手动触发**：在 GitHub 仓库的 `Actions` -> `Check & Release PJSK APK` 页面，点击 `Run workflow` 即可随时手动检测并发布。
