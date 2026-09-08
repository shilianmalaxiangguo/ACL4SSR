# ACL4SSR Full NoAuto 个人扩展

以 [ACL4SSR_Online_Full_NoAuto.ini](../Clash/config/ACL4SSR_Online_Full_NoAuto.ini) 为底稿，保留全部原有服务分类及规则源，增加刷帖、独立 Steam、TikTok、谷歌服务和 Github。ACL4SSR 原作及本目录派生配置遵循 [CC-BY-SA-4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.zh)。基线为本 fork 的 `f7c4233`，图标扩展提交为 `0450624`，2026-09-08 核验。

## 使用哪个文件

| 文件 | 作用 |
| --- | --- |
| [ACL4SSR_Online_Full_Personal_NoAuto.ini](ACL4SSR_Online_Full_Personal_NoAuto.ini) | 分组、默认选项、规则顺序的维护源；属于 subconverter 外部配置语法 |
| [mihomo-base.yaml](mihomo-base.yaml) | Windows Fake-IP/DNS 基础配置 |
| [group-ui.yaml](group-ui.yaml) | 妙妙屋/Mihomo 代理组图标元数据；用 Emoji，避免远程图片依赖 |
| [acl4-full-personal__v3.yaml](acl4-full-personal__v3.yaml) | 生成的妙妙屋 X / Mihomo YAML 模板，节点由面板注入 |
| [acl4-full-personal.candidate.lcf](acl4-full-personal.candidate.lcf) | Loon 候选模板；尚未完成当前 X 后端和设备验证 |
| [build.py](build.py) | 从同一 INI 生成 YAML 与 Loon 候选，避免手动维护两套策略 |

所有文件均不含节点凭据。YAML 的 `proxies: null`、Loon 的空 `[Proxy]` 是待注入位置，不能直接当成带节点的订阅使用。不要把 INI 当成 YAML 上传。生成器只支持本目录使用的 `select`、单个节点筛选表达式、HTTPS 文本规则和明确列出的内联规则，并不等于通用 subconverter。`group-ui.yaml` 中的 `icon` 会被写入 YAML 的 `proxy-groups[].icon`；它不是 Surge 的 `icon-url`，也不是妙妙屋网站 Logo。

## 分组与默认值

共 29 个手动选择组，无自动测速切换：

- 香港、美国、日本：沿用上游已有地区组，调整名称匹配；仅保留现有三地。
- 节点选择、刷帖：默认香港。刷帖匹配 NodeSeek、V2EX、Linux.do 及子域名。
- AI 服务：默认美国，日本可选；规则提前到微软、谷歌和 Github 之前。
- TikTok：默认日本，美国和香港可选；分流不等于地区解锁。
- 游戏平台、独立 Steam：默认 DIRECT，香港等可选。SteamCN 仍优先全球直连；该上游列表包含 steamcontent.com、steamusercontent.com 等较宽的后缀，并非精确的中国 CDN 地理识别。
- 油管、奈飞、国外媒体、电报、谷歌服务、Github：默认跟随节点选择。
- 哔哩哔哩、国内媒体、苹果、微软、Bing、OneDrive、谷歌 FCM、网易音乐：默认直连。
- 广告拦截、应用净化：默认 REJECT，可手动切换 DIRECT。
- 全球直连和漏网之鱼：保留原版选择组。

上游的台湾、新加坡、韩国及按名字猜测的“奈飞节点”筛选组未生成，避免当前三条自建节点产生空组；巴哈姆特服务组仍保留，默认跟随节点选择，但当前没有台湾出口，不保证地区内容可用。地区默认值为新配置的第一选项；客户端保存过同名组选择时可能恢复旧选项，需检查。

## 日常维护

修改个人 INI 即可维护策略。例如增加论坛：

```ini
ruleset=📰 刷帖,[]DOMAIN-SUFFIX,example.org
```

将它放在现有三条刷帖规则旁。调整默认出口时，把对应 `custom_proxy_group` 的目标选项放到第一位。Windows DNS 则编辑 `mihomo-base.yaml`。

安装 Python 和 PyYAML 后，在仓库根目录运行：

```text
python -m pip install PyYAML
python Personal/build.py
```

将修改后的 INI、`group-ui.yaml`、基础 YAML 和生成结果一并提交到自己的 fork；不修改上游原文件。通用规则 URL 继续引用 ACL4SSR 官方，Github/GitLab 引用 blackmatrix7，从而接收规则源更新。Mihomo 规则集每 24 小时更新，下载使用“节点选择”。修改 INI 本身不会自动触发构建或自动同步妙妙屋的本地模板副本。

本目录发布在自己的 fork，可使用以下入口：

- [妙妙屋 YAML 的 Raw 地址](https://raw.githubusercontent.com/shilianmalaxiangguo/ACL4SSR/master/Personal/acl4-full-personal__v3.yaml)
- [个人 INI 的 Raw 地址](https://raw.githubusercontent.com/shilianmalaxiangguo/ACL4SSR/master/Personal/ACL4SSR_Online_Full_Personal_NoAuto.ini)，供支持该语法的转换器使用。

妙妙屋选择“使用模板”，导入生成的 YAML，选择港美日节点后预览生成结果。每次模板结构变化后需重新导入/保存。妙妙屋的“分类勾选”与“使用模板”是独立生成模式，模板已自带完整分类；首次使用先生成测试订阅，检查客户端是否恢复了旧的同名组选择。

2026-09-08 实测：新建模板选择 **Clash → 链接**，填写上方 YAML Raw 地址；文件已经是 V3 且自带 Fake-IP DNS，无需再执行 V2 转换。`📰 刷帖` 是策略组，三条 `DOMAIN-SUFFIX` 是把论坛流量送到该组的规则。GitHub 的 Sync fork、面板模板重新导入、客户端每 24 小时更新远程规则集，是三个独立动作。

MMWX 0.5.3 会把显式 `DIRECT` 也按 `filter` 过滤；生成器现在将明确列出的 DIRECT/REJECT 加入筛选表达式，保留网易音乐默认直连。港美两节点的实际套餐订阅通过 Mihomo 1.19.30 校验及两地 HTTPS 出口测试，刷帖、AI、GitHub、网易音乐分流通过；日本空组被面板移除，TikTok 此时首选美国。独立测试启用了本地 Fake-IP DNS、关闭 TUN；不代表系统级 DNS 无泄漏、流媒体地区解锁或手机客户端已验收。

## Loon 边界

Loon 使用独立的 DNS 配置以及文本远程规则，不能直接照搬 Mihomo DNS，也不能直接导入 Surge 配置。候选版把中国 IP 直连放在远程列表末尾，使用 ACL4SSR `ChinaIp.list`，与 Mihomo 的最终 GEOIP 数据来源不同。共享规则顺序、NameRegexFilter、节点注入及 REALITY/Vision 连接仍需在实际 Loon 上验证；当前文件不作为已验收的手机/Mac 正式订阅。

## 本轮验证（2026-09-07）

- 原版 31 个 HTTP 规则源全部保留，扩展后 35 个；服务组完整保留，现有三条节点各自唯一命中一个地区组。
- 注入实际节点的完整 YAML 通过 Mihomo 1.19.30 内核校验，35 个规则集加载成功。
- 香港、日本 HTTPS 出口正常；12 个实际连接分别命中刷帖、油管、谷歌、Github、Steam、游戏平台、哔哩哔哩、TikTok 及 SteamCN 例外的预期策略。
- 美国节点在本轮探测时发生 443 连接拒绝及超时，AI 美国出口的 6 项连接检查明确跳过；默认美国和 AI 优先级已通过结构检查。整体连接验证为部分完成，不宣称美国或 AI 已通过。
- 上游若干列表仍包含旧 `URL-REGEX` 行，Mihomo 不支持并跳过，其他有效规则正常加载；不能把保留源 URL 理解为所有原始行均生效。没有引入 MITM。
- 测试使用独立实例，绑定物理网卡并关闭测试实例 TUN/DNS；不代表日常 TUN DNS、流媒体/AI 地区解锁、速度或妙妙屋实际渲染已经验收。
