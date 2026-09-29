# CF 活动自动领取

穿越火线（CF）网页活动自动领取工具。用真实 Chrome 驱动，模拟人工点击，登录态本地保存、复用。

## 原理

1. **枚举活动**：调 WMP 活动列表接口，拿到全部活动 + 起止时间，只保留「进行中」的。无需登录。
2. **登录**：`login.py` 打开 CF 页面，你手动登录一次（扫码 / 账号密码 / 短信均可），程序检测到登录 Cookie 后把登录态存成 `auth.json`。
3. **领取**：加载 `auth.json`，逐个打开活动页，扫描页面里所有 frame 的领取按钮并点击，通过弹窗文字 / AMS 接口请求判断结果。

未登录时 CF 活动页会被一个登录遮罩盖住、点击全部失效，所以**领取前必须先登录一次**。

## 安装

```bash
cd /Users/zunf/code/cf
uv venv .venv --python 3.12
uv pip install --python .venv playwright requests
.venv/bin/playwright install chromium   # 首次；驱动本机 Chrome 时其实用不到，装了更稳妥
```

需要本机已安装 **Google Chrome**（脚本用 `channel="chrome"` 驱动真浏览器，避免被检测）。

## 使用

### 方式一：网页 UI（推荐）

一键启动（首次会自动建 venv、装依赖）：

```bash
./start.sh              # macOS / Linux
start.bat              # Windows 双击
```

macOS 想在 Finder 里双击启动，双击 `start.command`。

也可以手动跑：

```bash
.venv/bin/python ui.py
```

会自动打开浏览器（`http://127.0.0.1:8765/`）。页面上：

1. 点 **「开始登录（扫码）」** → 二维码直接显示在页面里，用手机 QQ 扫。
2. 扫完点 **「刷新活动列表」** 看有哪些活动。
3. 点 **「一键领取全部」**，结果和日志实时刷新在页面上。

默认浏览器是无头运行的（不弹 Chrome 窗口，二维码只在页面里），这样更清爽。如果哪天遇到领取被风控拦截，加 `--show-browser` 让真实窗口显示出来：

```bash
.venv/bin/python ui.py --show-browser
```

### 方式二：命令行

```bash
# 1. 登录一次（会弹出 Chrome，你手动登，登完自动保存）
.venv/bin/python login.py

# 2. 看看有哪些活动
.venv/bin/python main.py --list

# 3. 领取
.venv/bin/python main.py

# 调试：只处理前 3 个 / 只处理指定 URL
.venv/bin/python main.py --limit 3
.venv/bin/python main.py --url "https://cf.qq.com/cp/a20260819septfirst/index.html"
```

结果会打印在终端；异常页面截图存到 `output/<时间戳>/`。

## 定时任务（macOS）

```bash
bash install_schedule.sh          # 每天 10:30 自动领取
bash install_schedule.sh remove   # 卸载
```

登录态过期时定时任务会失败，重新跑一次 `login.py` 即可。

## 配置

复制 `config.example.json` 为 `config.json` 后按需改：

| 字段 | 说明 |
| --- | --- |
| `browser.headless` | 是否无头。**建议 false**，无头易被检测 |
| `browser.page_wait_ms` | 页面加载后等待多久再扫描（ms） |
| `claim.only_in_progress` | 只处理进行中的活动 |
| `claim.click_delay` | 每次点击之间的随机间隔（秒） |
| `activities.extra_urls` | 手动追加的活动链接 |
| `notify.webhook` | 企业微信/钉钉机器人 webhook，留空则不发 |

## 活动适配器（adapters.json）

通用扫描靠文案「领取」+ class 关键词（`lq`/`lingqu`/`claim`）识别按钮，大部分活动能自动搞定。
个别页面结构特殊时，用 `adapters.json` 精确指定：

```json
{
  "a20260819septfirst": {
    "pre_dismiss": [".close-btn"],
    "buttons": [".t2btn_lq", ".btn-ljlq"]
  }
}
```

- key 是活动 URL 里的一段特征字符串（匹配任意子串即生效）。
- `pre_dismiss`：点这些选择器，用来关掉挡路的弹窗 / 公告。
- `buttons`：直接指定领取按钮选择器，填了就不再走通用扫描。

## 常见问题

- **结果全是「需登录」**：登录态过期，重跑 `login.py`。
- **「点击失败」**：按钮被弹窗挡住，给该活动加 `pre_dismiss`。
- **「未知」**：截图在 `output/` 里，看看实际弹窗文字，必要时给该活动配 `buttons`。
- **「无可领取」**：页面确实是空的，或活动已结束 / 未开始。
