"""登录页与账号子页：由 stub 下发 2014 版启动链的网页层。

启动链（client 侧 config.ini 实证）：
    StartUrl = http://passport.86joy.com/index.php/gwz/client/login/
    GET  /index.php/gwz/client/login/      launcher 的 QWebView 打开这一页
    POST /index.php/gwz/client/login/      表单提交
    302  http://game-onisoul.86joy.com/client/app.html
             ?token=<hex>&id=<hex40>&container=cog&now=<epoch>
    FinalUrl -> app.html -> Unity WebPlayer -> app.unity3d

版式来源（全部是缓存里的原版字节，非重绘）：
    wrap_bg.jpg   677x509  页面底板
    spt-index.png 717x234  UI 雪碧图（5 菜单、公告框、QQ群图、用户名/密码标签、
                            输入框边框、金色按钮、勾选框）
    start.png     196x199  「開戰 / GAME START」圆形按钮
    client_login.css  原版样式表（gzip 解压后 3769 字节），在此内联复刻

交互来源（同样是缓存原件）：
    jquery-1.7.2.min.js / jquery.blockUI.js / alertPlugin.js / dialog.css
    alertPlugin 里的 the37.alert(msg, type, fn) 就是原版的页面内弹层：
    350px 黑底圆角、标题「完成了」/「出错啦」、一个「关闭」按钮。

容器行为（实测）：QWebView 把 <a> 的点击交给 QDesktopServices::openUrl，
裸链接不导航；因此所有入口都用 JS 的 location.href 发起，表单走 POST。
"""
from __future__ import annotations

import hashlib
import html
import secrets
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, unquote_plus

LOGIN_PATH = "/index.php/gwz/client/login/"
GAME_HOST = "game-onisoul.86joy.com"
APP_PATH = "/client/app.html"
IMG_BASE = "/client/login/"
JS_BASE = "/client/login/js/"

_HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>鬼武者Soul</title>
<link rel="stylesheet" href="{js}dialog.css">
<style>
body,h1,h2,h3,h4,h5,h6,p,dl,dt,dd,ul,ol,li,form,fieldset,button,input,textarea,th,td{margin:0;padding:0;}
body{font:12px/1.5 "Microsoft YaHei",arial,"Hiragino Sans GB";color:#404040;background:#1b0a22;}
ul,ol{list-style:none;}
a{text-decoration:none;color:#2965b1;}
a:hover{text-decoration:underline;}
fieldset,img{border:0;}
button,input,select,textarea{font-size:100%;}
table{border-collapse:collapse;border-spacing:0;}
.clearfix{*zoom:1;}
.clearfix:after{content:"";display:table;clear:both;overflow:hidden;}
.wrap{width:677px;height:509px;background:url({img}wrap_bg.jpg) no-repeat;margin:0 auto;position:relative;}
.wrap_sub{background-image:url({img}wrap_bg_sub.jpg);}
.main{padding:25px 15px;}
.menu{overflow:hidden;margin-bottom:67px;}
.menu a,.menu .tab,.news_list,.focus-pic .img-wrap,.qq-group,.ui-input-wrap,.ui-label,.ui-radio,.btn_reg,.btn_forget,.btn_pay,.btn_s{background:url({img}spt-index.png) no-repeat;}
.menu ul{width:120%;}
.menu li{float:left;width:117px;height:28px;margin-right:15px;}
.menu .tab{display:block;height:100%;cursor:pointer;}
.menu .fore1{background-position:0 0;}
.menu .fore2{background-position:-133px 0;}
.menu .fore3{background-position:-266px 0;}
.menu .fore4{background-position:-399px 0;}
.menu .fore5{background-position:-531px 0;}
.news{overflow:hidden;margin-bottom:5px;}
.news .date{float:right;display:inline;margin-right:10px;}
.news .news_bd{width:380px;float:left;}
.news .news_list{height:31px;line-height:31px;background-position:-712px 0;background-color:#000;margin-bottom:5px;padding-left:10px;font-size:13px;color:#ffffda;}
.news_list .txt{color:#ffffda;float:left;width:85%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer;}
.focus-pic{float:right;}
.focus-pic .img-wrap{width:250px;height:179px;background-position:0 -38px;}
.focus-pic .img-wrap .hit{display:block;height:100%;cursor:pointer;}
.qq-group{width:190px;height:120px;background-position:-252px -39px;padding-top:38px;float:left;margin-right:10px;-webkit-box-sizing:border-box;box-sizing:border-box;}
.qq-group p{font-size:14px;color:#fff;text-align:center;margin-bottom:25px;}
.login{position:relative;padding-top:20px;float:left;width:447px;}
.login .l_list{height:31px;margin-bottom:15px;}
.ui-label{float:left;width:50px;height:20px;text-indent:-999em;margin:5px 10px 0 0;}
.ui-input-wrap{float:left;width:145px;height:29px;line-height:29px;padding:1px 6px;background-position:-522px -60px;}
.ui-input{height:29px;width:137px;border:0;background:none;line-height:29px;font-size:18px;color:#000;padding:0 4px;}
.ui-radio{float:left;width:15px;height:15px;background-position:100% -197px;margin:3px 0 0 10px;cursor:pointer;}
.ui-radio.checked{background-position:100% -212px;}
.label-user{background-position:-458px -65px;}
.label-pwd{background-position:-458px -114px;}
.btn_submit{position:absolute;width:196px;height:199px;background:url({img}start.png) no-repeat;border:0;cursor:pointer;right:-7px;top:-10px;}
.btn_reg,.btn_forget,.btn_pay,.btn_s{width:85px;height:28px;line-height:28px;text-align:center;color:#401500;display:inline-block;background-position:-455px -169px;font-weight:bold;font-size:14px;cursor:pointer;border:0;padding:0;font-family:inherit;}
.btn_reg:hover,.btn_forget:hover,.btn_pay:hover,.btn_s:hover{text-decoration:none;}
.err{position:absolute;left:15px;bottom:2px;font-size:12px;color:#ffd9c7;}
.band{position:absolute;left:16px;top:83px;height:31px;}
.band .tt{display:inline-block;height:31px;line-height:31px;padding:0 16px;background:rgba(10,4,14,.68);border:1px solid rgba(200,160,60,.38);color:#f2dc9c;font-size:15px;letter-spacing:1px;}
.panel{margin-top:18px;background:rgba(0,0,0,.60);border:1px solid #b8912f;padding:18px 22px;color:#efe4cf;}
.panel h2{font:normal 18px/1.3 "Microsoft YaHei",SimSun;color:#f2dc9c;margin:0 0 4px;}
.panel .lead{font-size:12px;line-height:1.8;color:#cbbda0;margin:0 0 14px;}
.panel .fieldrow{height:34px;margin-bottom:10px;}
.panel .fieldrow .ui-label{float:left;}
.panel .fieldrow .ui-input-wrap{float:left;width:250px;padding:1px 6px;}
.panel .fieldrow .ui-input{width:242px;font-size:16px;}
.panel .fields{overflow:hidden;}
.panel .btnrow{margin-top:12px;}
.panel .tip{font-size:12px;line-height:1.9;color:#d9c9a3;}
.panel .tip_strong{color:#f2dc9c;}
</style>
</head>
<body>
"""

_SCRIPT = """<script src="{js}jquery-1.7.2.min.js"></script>
<script src="{js}jquery.blockUI.js"></script>
<script src="{js}alertPlugin.js"></script>
<script>
function go(p){ if(p==="login"){ location.href="{action}"; return; } location.href="{action}?page="+p; }
{dialog}
(function(){
  var i=new Image();
  i.src="{action}?page=vp&w="+window.innerWidth+"&h="+window.innerHeight
       +"&sw="+screen.width+"&sh="+screen.height;
})();
/* 仅记住账号。兼容 QtWebKit，不保存或恢复密码。 */
(function(){
  var CK="oni_account";
  function getCookie(n){
    var m=document.cookie.match(new RegExp("(^| )"+n+"=([^;]*)(;|$)"));
    return m?m[2]:"";
  }
  function setCookie(n,v,days){
    var d=new Date(); d.setTime(d.getTime()+(days*24*60*60*1000));
    document.cookie=n+"="+v+";expires="+d.toUTCString()+";path=/";
  }
  // Every account page clears the legacy password-bearing cookie, even without a form.
  setCookie("oni_login","",-1);
  var box=document.getElementById("remember");
  var form=document.querySelector("form");
  if(!box||!form){ return; }
  var acc=form.querySelector('input[name="account"]');
  function isChecked(){ return box.className.indexOf("checked")>=0; }
  var saved=getCookie(CK);
  if(saved){
    try{
      var o=JSON.parse(decodeURIComponent(saved));
      if(o&&typeof o.a==="string"&&o.a){ acc.value=o.a; box.className="ui-radio checked"; }
      else{ box.className="ui-radio"; }
    }catch(e){ box.className="ui-radio"; }
  }
  box.onclick=function(){
    box.className = isChecked() ? "ui-radio" : "ui-radio checked";
    if(!isChecked()){ setCookie(CK,"",-1); }
  };
  form.onsubmit=function(){
    if(isChecked()&&acc.value){
      setCookie(CK, encodeURIComponent(JSON.stringify({a:acc.value})), 180);
    }else{
      setCookie(CK,"",-1);
    }
  };
})();
</script>
</body>
</html>
"""

_MENU = """    <div class="menu">
      <ul>
        <li><span class="tab fore1" onclick="go('official')"></span></li>
        <li><span class="tab fore2" onclick="go('notice')"></span></li>
        <li><span class="tab fore3" onclick="go('register')"></span></li>
        <li><span class="tab fore4" onclick="go('pay')"></span></li>
        <li><span class="tab fore5" onclick="go('service')"></span></li>
      </ul>
    </div>"""

_NEWS_ROW = """        <div class="news_list"><span class="txt" onclick="go('notice')">{text}</span><span class="date">{date}</span></div>"""

_NEWS = [
    ("本地 stub 已接管登录页与账号校验", "07-12"),
    ("启动链：登录页 -&gt; app.html -&gt; app.unity3d", "07-12"),
    ("账号任意填写，密码 3 位以上即可进入", "07-13"),
    ("client-onisoul 资源包按需回源，已接入缓存", "07-13"),
    ("进游戏后的接口按 402 端点契约应答", "07-14"),
]

_LOGIN_BODY = """<div class="wrap">
  <form method="post" action="{action}">
  <div class="main">
{menu}
    <div class="news">
      <div class="news_bd">
{news}
      </div>
      <div class="focus-pic"><div class="img-wrap"><span class="hit" onclick="go('notice')"></span></div></div>
    </div>
    <div class="clearfix"></div>
    <div class="qq-group">
      <p>官方QQ群</p>
      <p>stub 联调环境</p>
    </div>
    <div class="login">
      <div class="l_list">
        <span class="ui-label label-user"></span>
        <span class="ui-input-wrap"><input class="ui-input" type="text" name="account" value="{account}" maxlength="32"></span>
        <span class="ui-radio" id="remember" title="仅记住账号，不保存密码" aria-label="仅记住账号"></span>
      </div>
      <div class="l_list">
        <span class="ui-label label-pwd"></span>
        <span class="ui-input-wrap"><input class="ui-input" type="password" name="password" value="" maxlength="32" autocomplete="off"></span>
      </div>
      <input class="btn_submit" type="submit" value="">
    </div>
    <div class="clearfix"></div>
    <div>
      <span class="btn_reg" onclick="go('register')">注册新账号</span>
      <span class="btn_forget" onclick="go('recover')">找回密码</span>
      <span class="btn_pay" onclick="go('pay')">游戏充值</span>
    </div>
  </div>
  <div class="err">{error}</div>
  </form>
</div>"""

_SUBPAGE = """<div class="wrap wrap_sub">
  <div class="band"><span class="tt">{title}</span></div>
  <div class="main">
{menu}
    <div class="panel">
{content}
    </div>
  </div>
</div>"""

_REGISTER = """
      <p class="lead">填写账号与密码，提交后即可回登录页进入游戏。</p>
      <form method="post" action="{action}?page=register">
        <div class="fields">
          <div class="fieldrow">
            <span class="ui-label label-user"></span>
            <span class="ui-input-wrap"><input class="ui-input" type="text" name="account" value="{account}" maxlength="32"></span>
          </div>
          <div class="fieldrow">
            <span class="ui-label label-pwd"></span>
            <span class="ui-input-wrap"><input class="ui-input" type="password" name="password" value="" maxlength="32"></span>
          </div>
        </div>
        <div class="btnrow">
          <input class="btn_s" type="submit" value="注 册">
          <span class="btn_s" onclick="go('login')">返回登录</span>
        </div>
      </form>
      <p class="tip">{tip}</p>"""

_RECOVER = """
      <p class="lead">原站找回密码走 passport 服务，该服务已下线；stub 阶段任意密码都能登录。</p>
      <div class="btnrow">
        <span class="btn_s" onclick="go('login')">返回登录</span>
      </div>"""

_PAY = """
      <p class="lead">原站充值走 pay 网关，链接与页面均已下线；stub 无充值链路。</p>
      <div class="btnrow">
        <span class="btn_s" onclick="go('login')">返回登录</span>
      </div>"""

_SERVICE = """
      <p class="lead">原站客服系统已下线，此处保留入口。</p>
      <div class="btnrow">
        <span class="btn_s" onclick="go('login')">返回登录</span>
      </div>"""

_OFFICIAL = """
      <p class="lead">原站 gwz 门户已下线，此处保留入口。</p>
      <div class="btnrow">
        <span class="btn_s" onclick="go('login')">返回登录</span>
      </div>"""

_NOTICE = """
      <p class="tip">{rows}</p>
      <div class="btnrow">
        <span class="btn_s" onclick="go('login')">返回登录</span>
      </div>"""

_PAGE_MAP = {
    "register": ("注册新账号", _REGISTER),
    "recover": ("找回密码", _RECOVER),
    "pay": ("游戏充值", _PAY),
    "service": ("客服中心", _SERVICE),
    "official": ("官方网站", _OFFICIAL),
}


def matches(path: str) -> bool:
    p = (path or "").split("?")[0]
    return p.rstrip("/") == LOGIN_PATH.rstrip("/")


def page_of(query: str) -> str:
    if not query:
        return ""
    return (parse_qs(query, keep_blank_values=True).get("page") or [""])[0]


def parse_form(raw: bytes, content_type: str) -> dict[str, str]:
    ctype = (content_type or "").lower()
    if not raw:
        return {}
    if "application/x-www-form-urlencoded" in ctype or not ctype:
        data = parse_qs(raw.decode("utf-8", "replace"), keep_blank_values=True)
        return {k: v[0] for k, v in data.items()}
    try:
        data = parse_qs(unquote_plus(raw.decode("utf-8", "replace")), keep_blank_values=True)
        return {k: v[0] for k, v in data.items()}
    except Exception:
        return {}


@dataclass(frozen=True)
class LoginResult:
    status: int
    body: bytes
    location: str | None = None
    content_type: str = "text/html; charset=utf-8"


def _fill(template: str, values: dict[str, str]) -> bytes:
    text = template
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text.encode("utf-8")


def _document(body: str, dialog_js: str = "") -> bytes:
    base = {"img": IMG_BASE, "js": JS_BASE, "action": LOGIN_PATH, "dialog": dialog_js}
    text = _HEAD + body + _SCRIPT
    for key, value in base.items():
        text = text.replace("{" + key + "}", value)
    return text.encode("utf-8")


def _news_rows() -> str:
    return "\n".join(_NEWS_ROW.replace("{text}", t).replace("{date}", d) for t, d in _NEWS)


def render(account: str = "", password: str = "", error: str = "") -> bytes:
    # Keep the legacy argument for callers, but never echo credentials into HTML.
    body = _LOGIN_BODY.replace("{menu}", _MENU).replace("{news}", _news_rows())
    body = body.replace("{account}", html.escape(account, quote=True))
    body = body.replace("{error}", html.escape(error))
    return _document(body)


def _sub(title: str, content: str, dialog_js: str = "") -> bytes:
    return _document(_SUBPAGE.replace("{menu}", _MENU)
                     .replace("{title}", html.escape(title))
                     .replace("{content}", content), dialog_js)


def render_register(account: str = "", tip: str = "注册后账号写入服务器数据库；未注册的账号无法登录。") -> bytes:
    content = _REGISTER.replace("{account}", html.escape(account, quote=True)).replace("{tip}", html.escape(tip))
    return _sub("注册新账号", content)


def render_info(page: str) -> bytes:
    if page == "notice":
        title = "活动公告"
        content = _NOTICE.replace("{rows}", "<br>".join('%s　%s' % (d, t) for t, d in _NEWS))
    else:
        title, content = _PAGE_MAP.get(page, ("提示", ""))
        content = content or ""
    return _sub(title, content)


def register_submit(form: dict[str, Any]) -> LoginResult:
    account = str(form.get("account") or "").strip()
    password = str(form.get("password") or "").strip()
    if not account or len(account) > 32:
        return LoginResult(200, _register_error("账号不能为空，且不超过 32 位"))
    if len(password) < 3:
        return LoginResult(200, _register_error("密码至少 3 位"))
    status, reason = register_user(account, password)
    if status == "exists":
        return LoginResult(200, _register_error(reason))
    if status != "ok":
        return LoginResult(200, _register_error(reason))
    dialog = (
        "jQuery(function(){ the37.alert(%r, 1, function(){ location.href=\"%s\"; }); });"
        % ("账号已创建：" + account + "，点关闭回到登录页", LOGIN_PATH)
    )
    content = ('<p class="lead">账号 <span class="tip_strong">%s</span> 已创建。</p>'
               '<div class="btnrow"><span class="btn_s" onclick="go(\'login\')">返回登录</span></div>'
               % html.escape(account))
    return LoginResult(200, _sub("注册新账号", content, dialog))


def _register_error(msg: str) -> bytes:
    dialog = "jQuery(function(){ the37.alert(%r, 0); });" % msg
    content = ('<p class="lead">%s</p>'
               '<div class="btnrow"><span class="btn_s" onclick="go(\'register\')">重新填写</span></div>'
               % html.escape(msg))
    return _sub("注册新账号", content, dialog)

def redirect_url(token: str, ident: str) -> str:
    return (
        f"http://{GAME_HOST}{APP_PATH}"
        f"?token={token}&id={ident}&container=cog&now={int(time.time())}"
    )


_USERS_DDL = """
CREATE TABLE IF NOT EXISTS users (
  account_key   VARCHAR(64)  NOT NULL,
  password_hash VARCHAR(128) NOT NULL,
  salt          VARCHAR(64)  NOT NULL,
  created_at    DOUBLE       NOT NULL,
  PRIMARY KEY (account_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
"""


def _account_key(account: str) -> str:
    return " ".join(str(account or "").strip().split())


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 12000
    ).hex()


def _users_db():
    from app import db

    return db.connection()


def ensure_users_table() -> None:
    try:
        with _users_db() as con:
            with con.cursor() as cur:
                cur.execute(_USERS_DDL)
    except Exception as exc:
        print(f"[stub][users] 建表失败: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)


def register_user(account: str, password: str) -> tuple[str, str]:
    """返回 (状态, 给用户看的说明)。状态：ok / exists / error。"""
    key = _account_key(account)
    salt = secrets.token_hex(16)
    pwd_hash = _hash_password(password, salt)
    try:
        with _users_db() as con:
            with con.cursor() as cur:
                cur.execute(_USERS_DDL)
                cur.execute("SELECT account_key FROM users WHERE account_key = %s", (key,))
                row = cur.fetchone()
                if row:
                    return "exists", "该账号已注册，请直接登录或换一个账号"
                cur.execute(
                    "INSERT INTO users (account_key, password_hash, salt, created_at) "
                    "VALUES (%s, %s, %s, %s)",
                    (key, pwd_hash, salt, time.time()),
                )
    except Exception as exc:
        print(f"[stub][register] 落库失败: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return "error", "服务器写入账号失败，请稍后重试"
    print(f"[stub][register] 已落库 account={key}", file=sys.stdout, flush=True)
    return "ok", ""


def verify_user(account: str, password: str) -> str:
    """返回 ok / no_user / bad_password / error。"""
    key = _account_key(account)
    try:
        with _users_db() as con:
            with con.cursor() as cur:
                cur.execute(_USERS_DDL)
                cur.execute(
                    "SELECT password_hash, salt FROM users WHERE account_key = %s", (key,)
                )
                row = cur.fetchone()
                if not row:
                    return "no_user"
                stored = row["password_hash"] if isinstance(row, dict) else row[0]
                salt = row["salt"] if isinstance(row, dict) else row[1]
                if _hash_password(password, salt) != stored:
                    return "bad_password"
                return "ok"
    except Exception as exc:
        print(f"[stub][login] 校验失败: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return "error"


def _issue(account: str) -> tuple[str, str]:
    ident = secrets.token_hex(20)
    try:
        from app import sessions

        session = sessions.issue(account)
        return str(session["token"]), ident
    except Exception as exc:
        print(f"[stub][login] 会话不可用，退化 token: {type(exc).__name__}: {exc}", file=sys.stderr)
        return secrets.token_hex(16), ident


def submit(form: dict[str, Any]) -> LoginResult:
    account = str(form.get("account") or "").strip()
    password = str(form.get("password") or "").strip()
    if not account or not password:
        return LoginResult(200, render(account, error="用户名与密码不能为空"))
    if len(password) < 3:
        return LoginResult(200, render(account, error="密码至少 3 位"))
    state = verify_user(account, password)
    if state == "no_user":
        return LoginResult(200, render(account, error="该账号尚未注册，请先点「注册新账号」"))
    if state == "bad_password":
        return LoginResult(200, render(account, error="密码错误"))
    if state != "ok":
        return LoginResult(200, render(account, error="服务器校验失败，请稍后重试"))
    token, ident = _issue(account)
    location = redirect_url(token, ident)
    print(
        "[stub][login] session issued; redirecting to app",
        file=sys.stdout,
        flush=True,
    )
    return LoginResult(302, b"", location=location)


def handle_post(form: dict[str, Any], page: str = "") -> LoginResult:
    if page == "register":
        return register_submit(form)
    return submit(form)


def _viewport(query: str) -> None:
    data = parse_qs(query, keep_blank_values=True)
    values = {k: (data.get(k) or [""])[0] for k in ("w", "h", "sw", "sh")}
    print(
        "[stub][login] 容器视口 inner={w}x{h} screen={sw}x{sh}".format(**values),
        file=sys.stdout,
        flush=True,
    )


_users_ready = False


def handle_get(query: str, head_only: bool = False, user_agent: str = "") -> LoginResult:
    global _users_ready
    if not _users_ready:
        ensure_users_table()
        _users_ready = True
    if user_agent:
        print(f"[stub][login] GET ua={user_agent[:120]}", file=sys.stdout, flush=True)
    page = page_of(query)
    if page == "vp":
        _viewport(query)
        return LoginResult(200, b"<!DOCTYPE html><html><body style=\"background:#1b0a22\"></body></html>")
    if page == "register":
        return LoginResult(200, render_register())
    if page in {"recover", "pay", "service", "notice", "official"}:
        return LoginResult(200, render_info(page))
    return LoginResult(200, render())
