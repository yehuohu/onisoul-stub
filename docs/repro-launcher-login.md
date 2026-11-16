# 本地复现：鬼武者魂.exe → 登录页 → 注册账号 → 开战

本文让人在自己机器上把**启动器到打开游戏页**这一段跑起来。所有页面与脚本都来自客户端自带 WebKit 缓存里的原版字节，不是我凭空写的；下面每个文件都标了它在缓存里的记录名，可以逐字节对回去。

## 一、这一版能复现到哪一步

| 环节 | 状态 |
|---|---|
| 双击 鬼武者魂.exe，容器内出现登录页 | 可以（原版三张图 + 原版 CSS 数值） |
| 登录页六个入口（官网/公告/注册/充值/客服、顶部菜单）在窗口内换页 | 可以 |
| 注册账号 → 原版 `the37.alert` 弹层提示 | 可以（提示文案走缓存里的 `alertPlugin.js`） |
| 开战 → 302 → `/client/app.html` → 原版 app 页 | 可以（页面与脚本都是原件） |
| 开战之后 Unity 客户端真的启动并登录 | **可以**（实测 `/api/auth/gameLogin` 200，随后 `periodicInquiry`/`getServerTime`/`politic/map/cleanup`/`quest/checkEmergencyQuest` 全 200） |
| 起角色名 → 确认设定 → 建号 | **服务端已通，真机待复验**。原先 `registerName` 500 `MissingTableError`、`createPlayer` 判 `invalid countryId`、随后又报 `state changed concurrently`，三处均为服务端缺表/版本号实现缺陷，已修（见第八节）。服务端直接调用验证：`registerName → succeeded:true`、`createPlayer → succeeded:True`；真机上尚未复验到主城 |

> 2026-11-14 18:04、18:05 两次真机实测的请求序列（`logs/capture-*.jsonl`）：
> `POST /index.php/gwz/client/login/` 302 → `GET /client/app.html` 200 → `GET /client/js/revision.js` 200
> → `POST /api/auth/gameLogin` 200 → `POST /api/common/periodicInquiry` 200 → `POST /api/common/getServerTime` 200
> → `POST /api/politic/map/cleanup` 200 → `POST /api/quest/checkEmergencyQuest` 200 → 起名 `POST /api/auth/registerName` 500 ×10。

## 二、文件清单与证据来源

缓存解析方式：WebKit 的 `.d` 是一条完整 HTTP 事务（头 + 响应体）。文本/样式体多为 zlib（`78 9c` 起），图片取 `FFD8…FFD9`（JPEG）或 `89 50 4E 47 … IEND`（PNG）。记录名对应 `cache/data7/<md5首字符>/<记录名>.d`。

### 登录页（服务器下发，路径 `/index.php/gwz/client/login/`）

| 仓库路径 | 大小 | 缓存记录 |
|---|---|---|
| `assets/pc/web/client/login/wrap_bg.jpg` | 64054 | `38o89qw0.d` |
| `assets/pc/web/client/login/spt-index.png` | 118465 | `1jh1nvsg.d` |
| `assets/pc/web/client/login/start.png` | 67121 | `8e3ohvlu.d` |
| `assets/pc/web/client/login/wrap_bg_sub.jpg` | 70000 | **修补件，非原件**（见第五节第 3 条） |
| `assets/pc/web/client/login/js/jquery-1.7.2.min.js` | 94843 | `2qzg5nif.d` |
| `assets/pc/web/client/login/js/jquery.blockUI.js` | 19277 | `3q38dc2n.d` |
| `assets/pc/web/client/login/js/alertPlugin.js` | 2174 | `awnxane5.d` |
| `assets/pc/web/client/login/js/dialog.css` | 4729 | `14cwjsst.d` |

### app 页（`/client/app.html`）

| 仓库路径 | 大小 | 缓存记录 |
|---|---|---|
| `assets/pc/web/client/app.html` | 6502 | `2kwvyad3.d`（zlib，解压后 6541B 原文，减 1 处改动） |
| `assets/pc/web/client/app.css` | 2494 | `2l7v1vpi.d` |
| `assets/pc/web/client/js/jquery-1.7.2.min.js` | 94844 | `qfrkajch.d` |
| `assets/pc/web/client/js/jquery.cookie.js` | 1950 | `39sof5oa.d` |
| `assets/pc/web/client/js/UnityObject.js` | 21469 | `1uahvf53.d` |
| `assets/pc/web/client/js/login.js` | 3229 | `nf7kpngg.d` |
| `assets/pc/web/client/js/app.js` | 7112 | `1ks5jx17.d` |
| `assets/pc/web/client/js/commontool.js` | 6614 | `1ez9vc11.d` |
| `assets/pc/web/client/js/unityProxy.js` | 3244 | `3vrkhdsj.d` |
| `assets/pc/web/client/js/social.js` | 646 | `d9ghgrba.d` |
| `assets/pc/web/client/js/revision.js` | 34 | `3ar1l1in.d`（正文 `var ONI_SOUL_REVISION='30662007';`） |
| `assets/pc/web/client/img/getunity.png` | 5572 | `gyqmwqiu.d` |
| `assets/pc/web/client/img/logo.png` | 31042 | `12dlozfq.d` |
| `assets/pc/web/client/img/progressBar.png` | 2935 | `3dq73m4i.d` |
| `assets/pc/web/client/img/progressFrame.png` | 2939 | `h0u2d57l.d` |
| `assets/pc/web/client/img/bg_body.jpg` | 143538 | `1ddu8kvs.d`（app.html 的 body 背景，2500×800） |

## 三、复现步骤（Windows）

**前提**：Python 3.12+；该客户端为 `Cantainer` 外壳版本；需要管理员权限（占 80 端口）。

1. 取仓库并装依赖（登录链路不碰 MySQL，不配 `ONI_DB_*` 也能起）：

```powershell
git clone git@github.com:hcmjzq-png/onisoul-stub.git
cd onisoul-stub
pip install -r requirements.txt
```

2. 加 hosts（管理员打开 `C:\Windows\System32\drivers\etc\hosts`）：

```
127.0.0.1 passport.86joy.com
127.0.0.1 game-onisoul.86joy.com
127.0.0.1 client-onisoul.86joy.com
```

3. 起 stub（18080，绑回环）：

```powershell
$env:ONI_ROOT = (Get-Location).Path
python -m app.main --host 127.0.0.1 --port 18080
```

4. 起 80 端口转发（管理员，仓库自带脚本）：

```powershell
python tools\proxy80.py --listen 80 --upstream 18080
```

5. 双击 **鬼武者魂.exe**。

`Cantainer\config.ini` 与根目录 `config.ini` 保持默认即可，不要改：
- `StartUrl=http://passport.86joy.com/index.php/gwz/client/login/`
- `FinalUrl=http://game-onisoul.86joy.com/client/app.html`

## 四、预期结果与验收命令

登录页出现 5 个金边菜单 + 中间公告栏 + 用户名/密码 + 圆形「開戰」+ 三个小金按钮，右侧立绘完整。

```powershell
# 登录页
curl.exe -s -o NUL -w "%{http_code} %{size_download}`n" "http://passport.86joy.com/index.php/gwz/client/login/"
# 期望 200 7604

# 注册子页
curl.exe -s -o NUL -w "%{http_code} %{size_download}`n" "http://passport.86joy.com/index.php/gwz/client/login/?page=register"
# 期望 200 6554

# 注册提交（账号任意，密码 ≥3 位）
curl.exe -s -o NUL -w "%{http_code} %{size_download}`n" -d "account=demo&password=pass" "http://passport.86joy.com/index.php/gwz/client/login/?page=register"
# 期望 200 5932，页面自身加载后弹「完成了」

# 开战
curl.exe -s -o NUL -w "%{http_code} %{size_download}`n" -d "account=demo&password=pass" "http://passport.86joy.com/index.php/gwz/client/login/"
# 期望 302，Location 含 /client/app.html?token=…&id=…

# app 页
curl.exe -s -o NUL -w "%{http_code} %{size_download}`n" "http://game-onisoul.86joy.com/client/app.html"
# 期望 200 6502
```

服务端日志（`logs/stub-systemd.log` 或控制台）会打出：

```
[stub][login] GET ua=Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/534.34 …
[stub][login] 容器视口 inner=680x510 screen=1920x1080
[stub][register] account=demo
[stub][login] account=demo token=… id=… -> http://game-onisoul.86joy.com/client/app.html?token=…
```

## 五、与原版的差异（逐条，别当成还原度）

1. **`app.html` 改了一行**：body 背景 `url(http://static.86joy.com/gameweb/gwz/images/bg_body.jpg)` → `url(img/bg_body.jpg)`。该域名现返回 502，原件已从缓存取出放 `img/`。其余字节未动。
2. **登录页 HTML 本身没有原件**：原站模板已删（现返回 ThinkPHP「模板不存在 [AUCenter/Tpl/Gwz/Default/Client_login.html]」），页面 HTML 也不会进 WebKit 缓存（响应带 `Cache-Control: no-store`）。所以页面结构是按缓存里 `passport` 侧 CSS 数值 + 三张原图重建的。
3. **入口不能用 `<a href>`**：exe 内嵌 `linkClicked(QUrl)` / `QDesktopServices::openUrl`，容器会把链接点击交给系统浏览器；裸 `<a>` 点了没反应。因此入口元素全部改成 `<span>` + `location.href` 跳转（已真机验证在窗口内换页）。
4. **`wrap_bg_sub.jpg` 是修补件**：原 `wrap_bg.jpg` 里 y=83~113 那 31 行把「游戏公告」四个字烘进像素。子页要显示各自标题，只能用镜像填充把那 31 行抹掉，再叠一条自绘的暗底金字标签。接缝处有一道很淡的水平痕迹，那块也没有原始卷轴饰带可用。
5. **注册不落库**：`register_submit` 只校验（账号非空 ≤32、密码 ≥3）并写日志，不写 users 表；登录校验同样不查库，任意账号密码 ≥3 位都能拿到 302。页面底部那行「stub 不落库，注册仅演示流程」就是这事。
6. **`app.unity3d` 不需要下发**：容器自带 Unity WebPlayer，客户端也自带 `app.unity3d`，真机从头到尾**没有请求过** `/client/app.unity3d`（capture 日志 0 条）。所以这个 4.0MB 包不入库不影响开战。
7. **起名卡点已定性为服务端缺陷，不是缺数据**：三处调用把「表里有内容」当成前提（`mission_chain.rows()` 缺表未容错、`create_player` 用 `beginning_equipment` 判国家、`_create_player` 重建默认态丢 `_revision`）。客户端只是如实把 `succeeded:false` 显示成「联机中断」。修复见第八节；`assets/pc/tables/` 仍为空，表内容缺失只影响数值与初始武将，不再打断请求。
8. **`/api/` 已通**：以前记录里「`/api/` 请求 0 条」的说法作废；现在 `gameLogin`、`periodicInquiry`、`getServerTime`、`politic/map/cleanup`、`quest/checkEmergencyQuest` 都是真实客户端发来的 200。

## 六、出问题怎么查

| 现象 | 先看什么 |
|---|---|
| 登录页白屏 | `curl` 登录页是否 200/7604；日志有没有 `[stub][login] GET ua=…` |
| 页面出来但样式全乱 | `/client/login/wrap_bg.jpg`、`spt-index.png`、`start.png` 是否 200 |
| 点入口没反应 | 页面里入口是不是被改回 `<a href>` 了（见第五节第 3 条） |
| 开战 404 | `assets/pc/web/client/app.html` 是否落位；`app/paths.py` 的 `ONI_PC_WEB_DIR` 是否指对 |
| 停在「讀取中」 | 看 capture 日志：`/api/auth/gameLogin` 是否 200；`/api/auth/registerName` 是否是 500（若是，先按第八节确认三处容错补丁还在） |
| 弹「联机中断(1)」 | 看 `POST /api/auth/createPlayer` 的 `resp_body`：`errorReason` 是 `invalid countryId` 或 `state changed concurrently; retry`，都属第八节那类缺陷 |
| 端口占用 | `netstat -ano | findstr ":80"` |

## 七、没做、也不打算在这版做的

- 108 张表 JSON 的导入（`assets/pc/tables/`）。缺表不再打断流程（第八节已容错），但初始武将、任务链、建筑等数值会是空的
- 游戏资源 bundle（`assets/pc/jp/assets/**` 数百个 `.unity3d`）；注意 `app.unity3d` 本身**不需要**，客户端自带
- 真实账号体系（登录/注册落库、token 校验）
- 子页版式与原版注册/找回页对照（原件不存在，当前统一用金色面板版式）

## 八、2026-11-14 追加：起名→建号链路上的三处服务端缺陷（已修）

三处是同一类写法：**把「服务端手里有那份客户端表」当成前提**。客户端本身从不向服务端要表（capture 日志 1185 条里 `.json` 仅 15 条，全是外部扫描器探测，游戏表请求 0 条），所以缺表时应当降级，而不是把请求打成失败。

| # | 位置 | 修复前行为 | 修复 |
|---|---|---|---|
| 1 | `app/business/mission_chain.py` 的 `rows()` | 直接 `catalog.load("politicMission")`，缺表抛 `MissingTableError` → `registerName` 500 | 与 `GameplayService._table()` 同策略：`except TableError: return {}` |
| 2 | `app/business/gameplay.py` 的 `create_player()` 国家校验 | `if country not in self._table("beginning_equipment")`，表空则任何 `countryId` 都判非法 → 客户端弹「联机中断(1)」 | 改为表非空时才校验 |
| 3 | `app/business/gameplay.py` 的 `create_player()` 保存 | `_create_player()` 用 `_default_state` 重建，丢 `_revision`；保存时期望 0、库里 1 → `StateConflictError` | 重建前取 `revision`，重建后写回 |

对应的日志原件（`logs/capture-20261114.jsonl`）：

```
19:10:20 POST /api/auth/registerName  500 {"error":"INTERNAL","message":"MissingTableError"} ×10
19:10:32 POST /api/auth/createPlayer  200 {"succeeded": false, "errorReason": "invalid countryId"}
19:13:59 POST /api/auth/createPlayer  200 {"succeeded": false, "errorReason": "state changed concurrently; retry"}
```

服务端直接调用回归（新号 `repro-0003`，先起名再建号）：

```
registerName: True
createPlayer: True
```

说明：本节只验证到「服务端不再拒绝该请求」，真机上从「最终决定」到主城是否走通，尚未复验。

## 九、2026-11-14 追加：账号鉴权改造，以及进主城后的资源卡点

### 9.1 注册落库 + 登录校验（commit `922a7d0`，PR #20）

改造前的行为是「任意账号 + 任意 ≥3 位密码都发 token」，注册页只做格式校验、不落库（页面明写「stub 不落库，注册仅演示流程」）。改造后：

- 新表 `users(account_key varchar(64) PK, password_hash varchar(128), salt varchar(64), created_at double)`，由登录页首次 GET 时惰性 `CREATE TABLE IF NOT EXISTS`，不依赖迁移脚本；
- 密码存 PBKDF2-HMAC-SHA256（12000 轮）+ 每账号 16 字节随机 salt，不存明文；
- 注册重复 → 「该账号已注册，请直接登录或换一个账号」；
- 登录未注册 → 「该账号尚未注册，请先点『注册新账号』」；密码错 → 「密码错误」；校验通过才 `sessions.issue` 发 token 并 302。

服务端 curl 实测（`http://127.0.0.1/index.php/gwz/client/login/`）：

```
1) POST account=authtest1&password=abc123  (?page=register)  → 200 页面含「账号已创建」
2) 同一账号再注册                                            → 200 页面含「该账号已注册」
3) POST account=ghost999&password=abc123                     → 200 页面含「该账号尚未注册」
4) POST account=authtest1&password=wrongpass                 → 200 页面含「密码错误」
5) POST account=authtest1&password=abc123                    → 302 → /client/app.html?token=…
```

库里 `users` 落了一行：`authtest1  aece2d94634b…  1794657595.9`。

### 9.2 「记住账号密码」勾选框（同 commit）

原页面 `#remember` 是个 `<span class="ui-radio checked">` 死图：没有 onclick，也没有任何持久化，点了没反应、下次也不记。现在：

- 点击切换 `ui-radio` / `ui-radio checked`；
- 勾着提交时把 `{a:账号, p:密码}` 写进 cookie `oni_login`（180 天），取消勾选提交则删除；
- 下次加载自动回填并置为选中；
- 用 `document.cookie` 而不是 `localStorage`——容器是 QtWebKit 4.x，localStorage 持久化没有保证。

边界：密码是明文存在客户端本机 cookie 里的，只适合本地 stub；要不要改成「只记账号」另行决定。登录页体积 7604 → 9031 字节，响应头 `Cache-Control: no-store, no-cache, must-revalidate`。

### 9.3 真机链路：建号这次真的成功了

```
20:01:16 POST /api/auth/registerName  200 {"succeeded": true}
20:01:26 POST /api/auth/createPlayer  200 {"succeeded": true, "playerId": "p_dc76e9f0c0006e8f"}
```

库里该玩家（`SELECT player_id, JSON_EXTRACT(state_json,'$.entity.created') …`）：

```
p_dc76e9f0c0006e8f   created=true   username=流音   country=country37   state 1101 字节
```

真机截图上 HUD 已渲染（编成／物语／合战／鬼签、商店／建筑／仓库／每日奖励），说明客户端已经过建号、进了主城骨架。

### 9.4 现行卡点：6 个 `chara/*.unity3d` 404 触发「联机中断(1)」

建号前后那几秒，所有 API 都是 200，唯一的失败请求是角色资源包：

```
20:01:17 404 /client/pc/jp/assets/chara/395a38ee07917a3f1342358cdb6c4fff.unity3d  ×5
20:01:18 404 /client/pc/jp/assets/chara/1450fa13b6e0098ea407efee5de253b2.unity3d  ×5
```

累计请求次数（`capture-20261114.jsonl` 全文 grep）：

```
16  chara/adab798b1a597e970fa1995aa4a9dd11.unity3d
15  chara/759f9e91a56a2aab75b1d64bf101a5ef.unity3d
11  chara/b6c88175b58f489bebf782eef21ace35.unity3d
11  chara/69e30186b8b4e5649be7b31103de7558.unity3d
10  chara/395a38ee07917a3f1342358cdb6c4fff.unity3d
 5  chara/1450fa13b6e0098ea407efee5de253b2.unity3d
```

两边都没有这些文件：

- 服务端：`PC_BUNDLE_DIR=/opt/onisoul/assets/pc/bundles`、`PC_CACHE_DIR=/opt/onisoul/assets/pc/cache` 两个目录 `exists: False`（`assets/pc` 下只有 `web`），`paths.py` 里那 6 条候选路径全部 miss；
- 客户端：`D:\鬼武者魂` 按这 6 个哈希名搜索命中 0；`cache` 下只有 `data7`（16 桶 163 条 `.d`）、`prepared`（0 文件）、`WebpageIcons.db`（68608 B），`WebPlayer\Cache\Temp` 0 文件；
- 源站：`client-onisoul.86joy.com` 在服务器上 `getent hosts` 解析失败、`curl` 报 `Could not resolve host`，不可回源。

结论：这 6 个包只能从**跑过原服、缓存里有副本的机器**上取（朋友机器 `D:\鬼武者魂\cache\data7` 里按哈希搜），拿到后落盘到 `assets/pc/bundles/chara/<hash>.unity3d`，「联机中断」才会消失。这是素材缺失，不是协议/逻辑错误，与第八节的三处服务端缺陷性质不同。

附带一个已知内容缺口：`createPlayer` 写入的 `characters` 是空的——`_initial_characters` 依赖 `beginning_equipment` + `item01` + `character` 三张表，表空则初始武将 0 个。所以即便资源包到位，主城／编成里的武将列表仍需要最小初始存档来填。

## 十、从客户端缓存还原 PC 资产包（方法进仓，二进制不入仓）

原站 `client-onisoul.86joy.com` 已不可访问（服务器上 `getent hosts` 解析失败、`curl` 报 `Could not resolve host`），所以 PC 版的 `.unity3d` 资产包只能从**跑过原服的机器上的缓存副本**还原。方法固化在 `tools/extract_cached_bundles.py`，二进制本身不进 git。

### 10.1 `.d` 记录格式（QtWebKit 4.x 磁盘缓存）

一条记录就是一笔 HTTP 事务：

```
偏移 0   4 字节  记录长度
偏移 4   4 字节  版本标记（观测值 0x00000007）
偏移 8   4 字节  URL 长度（大端）
偏移 12  N 字节  URL 明文（ASCII）
...              状态行 + 响应头
...              响应体
```

URL 按 MD5 首字符分到 `cache/data7/0` ~ `f` 共 16 个桶，记录文件名是 8 字符短名、与 URL 无关，因此必须逐条读 URL 才知道它是什么资源。

响应体两种形态：明文（包体以 `UnityWeb` 开头，`app.unity3d` 那 4 MB 就是这样，魔数落在记录内偏移 304 附近）或 zlib／gzip 压缩流（解压后才以 `UnityWeb` 开头）。脚本按这个顺序尝试。

### 10.2 本轮实测（2026-11-14，`DESKTOP-N8RCQR0`）

```
扫描 D:\鬼武者魂\cache\data7      164 条记录，43,414,472 B
匹配 /assets/<dir>/<hash>.unity3d  130 条命中（含 6 条重复 URL）
解出文件                          124 个，38,097,726 B
命中方式                          plain 124 / zlib 0 / gzip 0 / 失败 0
包体校验                          chara/1b3772… 前 8 字节 = UnityWeb
```

按目录：

```
bgm 3 / building 4 / cch 2 / chara 15 / item 40 / mission 1 / pbg 27
pbm 1 / product 1 / scene 11 / scr 14 / se 1 / vse 4
```

### 10.3 部署与验证

产物放在服务端 `/opt/onisoul/assets/pc/bundles`，正好命中 `app/transport/paths.py` 里静态层的第 1 条候选路径 `PC_BUNDLE_DIR/<dir>/<hash>.unity3d`。实测（`curl` 打 `127.0.0.1`，带 `?r=306620`）：

```
chara/1b3772fdd4b788f942075d29d2f32423 → 200 116,984 B
scene/7bf2c1d92f87d89a4f646a9cefb8fb62 → 200 2,622,889 B
bgm/5b7ebaae6b9ea0a8e79c014237bb83cd   → 200 1,510,109 B
```

这三条以前都是 404。

### 10.4 复现步骤

```bash
# 1) 在有缓存副本的 Windows 机器上解包（--dry-run 先看统计）
python3 tools/extract_cached_bundles.py --cache-dir "D:/鬼武者魂/cache/data7" --out ./bundles --dry-run
python3 tools/extract_cached_bundles.py --cache-dir "D:/鬼武者魂/cache/data7" --out ./bundles

# 2) 把 bundles/ 下各目录拷到服务端
rsync -r ./bundles/ ubuntu@<server>:/opt/onisoul/assets/pc/bundles/

# 3) 验证
curl -s -o /dev/null -w "%{http_code} %{size_download}\n" \
  "http://127.0.0.1/client/pc/jp/assets/chara/1b3772fdd4b788f942075d29d2f32423.unity3d?r=306620"
```

### 10.5 仍然缺的 6 个 chara 包

```
16 次请求  chara/adab798b1a597e970fa1995aa4a9dd11
15 次请求  chara/759f9e91a56a2aab75b1d64bf101a5ef
11 次请求  chara/b6c88175b58f489bebf782eef21ace35
11 次请求  chara/69e30186b8b4e5649be7b31103de7558
10 次请求  chara/395a38ee07917a3f1342358cdb6c4fff
 5 次请求  chara/1450fa13b6e0098ea407efee5de253b2
```

缓存里现有的 15 个 chara 包与这 6 个哈希**互不相同**（`c42732b9…`、`c07e9888…`、`84fa3ca2…`、`f1fc3313…`、`441147d9…`、`8b3d6b8a…`、`e2fba99c…`、`5fd8a8e6…`、`8151e5be…`、`616bf995…`、`497199bd…`、`1b3772fd…`、`58479003…`、`3e87841f…`、`5a10edfd…`），替补不了——这 6 个一直 404，失败响应不会进缓存。

要补齐只能从另一台跑过原服、缓存里有这些哈希的机器上取，再走同一套脚本。

## 十一、服务端的表从客户端包里抽（同源同版本）

服务端要自己有一套表：客户端表只服务表现层（它自己读，实测 1185 条请求里没有一条是取表的），服务端要用同一批数据做判定与发放。所以两套表必须是**同一份 JSON、同一 root_key、同一客户端版本**，不能各写一份。

抽取方法固化在 `tools/extract_tables_from_bundle.py`，表文件本身不进 git。

### 11.1 表在哪

PC 客户端的 108 张表不是独立文件，而是作为 JSON 文本内嵌在场景包里：`scene/1243ea6aa6…`（缓存记录 `1243ea6aa6…kbeizo6m` 无关，实际是 `data7` 里那一个），解压后 **100,194,188 B**，格式是

```
{"<root_key>": {"<行id>": {...}, ...}, "<另一个表>": {...}, ...}
```

`app.unity3d`（解压 19,463,656 B）里只有 `assetbundle` 这一张表（63 条，全是 `assets/scene/*.unity3d` 场景包清单），其余表都在场景包里。

### 11.2 本轮实测

```
清单条目            112（docs/analysis/table_list.tsv 108 + server_tables.tsv 4）
抽出成功            109 张（18,076,191 B）
另从 app.unity3d   assetbundle.json（63 条，11,506 B）
最终落盘            110 张，18 MB
TableCatalog 校验   110/112 通过，合计 40,160 行
```

按 `app/tables.py` 的强校验逐张加载，失败仅 2 张：

```
combo.json                MissingTableError
strategy_battlefield.json MissingTableError
```

这两张的缺失是**客户端本身没有随包**，不是抽取失败：

- 在 124 个已还原包 + `app.unity3d` 解压体里，`"combo"` 作为表名 0 命中；`app.unity3d` 里只有 `ComboTableAccessor` 类名与字段名 `comboCount`；
- `strategyBattlefield` / `strategy_battlefield` 在 `app.unity3d` 里 0 命中，任何包内也 0 命中。

### 11.3 建号回归（真表）

```
beginning_equipment  48 行，含 country37
country37            questCharacters [item01_0101201]
                     attackCharacters [item01_0936101]
                     defenseCharacters [item01_0936201 0936401 0936601 0936801 0936901]
_create_player()     characters = 7 个，counters.characterCount = 7
  1 -> chara1_01012_01  atk 1250 def 1250 int 1250
  2 -> chara1_09361_01  atk  600 def  350 int  300
  3 -> chara1_09362_01  atk  325 def  325 int  600
resources            gold/wood/food/iron 仍为 0（beginning_equipment 的 gold 字段未参与建号，见 gameplay.py 注释）
buildings 0 个，missions 1 条
```

也就是说：表到位后初始武将不再是空表结果，而是 7 个真角色；资源与建筑仍是各自逻辑的现状，不在本次改动范围。

### 11.4 复现

```bash
# 1) 解包场景包（从缓存记录里取，或直接用已还原的 scene/*.unity3d）
python3 tools/extract_tables_from_bundle.py --bundle ./scene/1243ea6aa6.unity3d \
    --out /opt/onisoul/assets/pc/tables

# 2) 校验（需要生产 env，否则连库会 1045）
sudo bash -c 'set -a; . /etc/onisoul/stub.env; set +a;
  export ONI_ROOT=/opt/onisoul ONI_TABLE_DIR=/opt/onisoul/assets/pc/tables;
  cd /opt/onisoul && python3 /tmp/verify_tables.py'

# 3) 只补缺失的表时加 --only-missing，不会覆盖已有文件
```

### 登录凭据隐私修复

新版登录页仅可选择记住账号（默认不勾选），不再保存或回填密码。
打开任意账号页面时会删除当前主机、`path=/` 的旧 `oni_login` Cookie；
取消记住账号时立即删除账号 Cookie，无须再次提交。
旧客户端须实际加载新版页面后才会执行迁移，不会远程清除尚未打开的客户端。

`tools/proxy80.py` 的抓包日志现在只保存路径、状态、耗时与报文大小，
不保存任何请求/响应正文，避免登录、注册、会话及未知协议字段中的凭据漏记。
转发内容不变。登录成功的服务日志也不再输出包含 token 的跳转地址。
这是有意收窄诊断日志；排查协议如需正文，应另行使用合成测试数据，勿记录真实凭据。

此代码变更不删除历史日志、不修改实际部署或网络监听配置，也不为旧 HTTP 链路提供加密。
历史日志和客户端缓存可能仍包含旧密码，需由维护者另行确认并处理；测试应使用独立密码。
