import contextlib
import io
import json
import shutil
import subprocess
import unittest
from unittest.mock import patch, MagicMock

from app.transport import login_page
from tools import proxy80


class LoginPrivacyTests(unittest.TestCase):
    def test_failures_never_echo_password(self):
        for state in ('no_user', 'bad_password', 'error'):
            with self.subTest(state=state), patch.object(login_page, 'verify_user', return_value=state):
                result = login_page.submit({'account': 'tester', 'password': 'secret<&>'})
                self.assertNotIn(b'secret', result.body)
                self.assertIn(b'value="tester"', result.body)
        self.assertNotIn(b'secret', login_page.render('tester', 'secret'))
        self.assertNotIn(b'value="xy"', login_page.submit({'account': 'tester', 'password': 'xy'}).body)

    def test_success_redirect_kept_but_not_logged(self):
        output = io.StringIO()
        with patch.object(login_page, 'verify_user', return_value='ok'), patch.object(login_page, '_issue', return_value=('secret-token', 'secret-id')), contextlib.redirect_stdout(output):
            result = login_page.submit({'account': 'tester', 'password': 'secret'})
        self.assertEqual(result.status, 302)
        self.assertIn('token=secret-token', result.location)
        self.assertNotIn('secret', output.getvalue())

    @unittest.skipUnless(shutil.which('node'), 'Node required for QtWebKit-compatible JavaScript behavior tests')
    def test_cookie_lifecycle(self):
        script = login_page._SCRIPT.split('/* 仅记住账号。', 1)[1].split('*/', 1)[1].split('</script>', 1)[0]
        harness = r'''
const assert = require('assert');
function run(initial, hasForm=true) {
  let jar = {...initial}, writes = [];
  let box = {className:'ui-radio'}, acc = {value:''};
  let form = {querySelector: () => acc};
  let document = {
    get cookie() {return Object.keys(jar).map(k=>k+'='+jar[k]).join('; ');},
    set cookie(v) {writes.push(v); let [pair,...attrs]=v.split(';'); let i=pair.indexOf('='); let k=pair.slice(0,i); let expires=attrs.find(a=>a.startsWith('expires=')); if(expires && new Date(expires.slice(8))<new Date()) delete jar[k]; else jar[k]=pair.slice(i+1);},
    getElementById:()=>hasForm?box:null,
    querySelector:()=>hasForm?form:null
  };
  eval(SCRIPT);
  return {jar,writes,box,acc,form};
}
let old=encodeURIComponent(JSON.stringify({a:'tester',p:'old-password'}));
let x=run({oni_login:old});
assert(!('oni_login' in x.jar)); assert.equal(x.acc.value,'');
assert.equal(x.box.className,'ui-radio');
x.acc.value='tester'; x.form.onsubmit(); assert(!('oni_account' in x.jar));
x.box.onclick(); x.form.onsubmit();
assert.deepEqual(JSON.parse(decodeURIComponent(x.jar.oni_account)),{a:'tester'});
assert(!x.writes.join('').includes('old-password'));
let y=run(x.jar); assert.equal(y.acc.value,'tester');
y.box.onclick(); assert(!('oni_account' in y.jar)); // cancellation without submit
assert(!('oni_login' in run({oni_login:old},false).jar)); // register/info page
assert.equal(run({oni_account:'%broken'}).box.className,'ui-radio');
'''
        subprocess.run(['node', '-e', 'const SCRIPT=' + json.dumps(script) + ';\n' + harness], check=True, capture_output=True)


class ProxyPrivacyTests(unittest.TestCase):
    def handler(self, path='/index.php/gwz/client/login/?page=register&token=secret'):
        h = object.__new__(proxy80.Handler)
        h._read_request = lambda: ('POST', path, {'content-type':'application/x-www-form-urlencoded'}, b'account=test&password=secret')
        h._send = MagicMock()
        return h

    def test_capture_omits_bodies_without_changing_forwarding(self):
        for path in ('/index.php/gwz/client/login/?page=register&token=secret', '/api/test/?token=secret', '/other'):
            h = self.handler(path)
            response = MagicMock(status=200)
            response.read.return_value = b'<input value="secret">'
            response.getheaders.return_value = [('Set-Cookie','session=secret')]
            conn = MagicMock(); conn.getresponse.return_value = response
            with patch.object(proxy80.http.client, 'HTTPConnection', return_value=conn), patch.object(proxy80, 'write_rec') as record:
                h.handle()
            self.assertNotIn('secret', json.dumps(record.call_args.args[0]))
            self.assertEqual(record.call_args.args[0]['req_size'], len(b'account=test&password=secret'))
            self.assertEqual(conn.request.call_args.kwargs['body'], b'account=test&password=secret')
            self.assertEqual(h._send.call_args.args[1], b'<input value="secret">')

    def test_error_drops_query_and_exception_detail(self):
        h = self.handler()
        with patch.object(proxy80.http.client, 'HTTPConnection', side_effect=OSError('secret')), patch.object(proxy80, 'write_rec') as record:
            h.handle()
        self.assertNotIn('secret', json.dumps(record.call_args.args[0]))
        self.assertEqual(record.call_args.args[0]['status'], 502)
