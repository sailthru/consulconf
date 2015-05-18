
import json
import nose.tools as nt
from os.path import abspath, dirname
from subprocess import check_call, check_output
import requests
from consulconf import configure_logging

CWD = dirname(abspath(__file__))
AGENT = "http://127.0.0.1:8500/v1/kv/consulconftest"

nt.assert_dict_equal.__self__.__class__.maxDiff = None


def setup_module():
    configure_logging(True)


def teardown_module():
    resp = requests.delete(AGENT, params={'recurse': True})
    assert resp.ok


def test_empty_ns_in_consul():
    fn = 'test_empty_ns_in_consul'
    check_call('consulconf -i %s -p %s/test-%s --delete'
               % (CWD, AGENT, fn), shell=True)
    nt.assert_dict_equal(
        json.loads(check_output(
            'consulconf -i %s/test-%s --dry_run' % (AGENT, fn), shell=True)
            .decode()),
        {
            "test": {},
            "test-namespace": {},
            "test-ns1": {"key1": "val1"},
            "test-ns2": {"key1": "val1"},
            "test/app1": {},
            "test/app2": {"key1": "val1"},
            "test/app20": {"key": "value"},
            "test/app21": {"key": "value", "key1": "val1"},
            "test/app22": {"key1": "val1"},
            "test/app3": {},
            "test/app4": {"key2": "val2"},
            "test/app5": {"key1": "val1", "key2": "val2"},
            "test/app6": {"key1": "val11"},
            "test/app7": {"key1": "val11", "key2": "val2"},
            "test/app8": {"key1": "val1", "key2": "val22"},
            "test/app9": {"key1": "val1", "key2": "val222"}
        }

    )


def test_filterns():
    dct = {
        'test/app3': {},
        'test/app4': {'key2': 'val2'},
        'test/app5': {'key1': 'val1', 'key2': 'val2'}}
    nt.assert_dict_equal(
        json.loads(check_output(
            "consulconf -i %s --dry_run --filterns '^.*app[345]$'" % (CWD),
            shell=True).decode()),
        dct)


def test_different_inputs_have_same_rv():
    fn = 'test_different_inputs_have_same_rv'
    check_call('consulconf -i %s -p %s/test-%s --delete'
               % (CWD, AGENT, fn), shell=True)
    nt.assert_dict_equal(
        json.loads(check_output(
            'consulconf -i %s/test-%s --dry_run' % (AGENT, fn), shell=True)
            .decode()
        ),
        json.loads(check_output(
            'consulconf -i %s --dry_run' % CWD, shell=True).decode())
    )


def test_option_raw():
    fn = 'test_option_raw'
    dct = {
        "test-namespace/_shared/key1": "val11",
        "test-namespace/_shared2/key2": "val22",
        "test-namespace/_shared3/key2": "val222",
        "test-namespace/_shared3/key3": "val3",
        "test-ns1/key1": "val1",
        "test-ns2/_inherit": "[\"test-ns1\"]",
        "test/_shared/key1": "val1",
        "test/_shared2/key2": "val2",
        "test/app2/_inherit": "[\"_shared\"]",
        "test/app20/key": "value",
        "test/app21/_inherit": "[\"_shared\"]",
        "test/app21/key": "value",
        "test/app22/_inherit": "[\"test-ns1\"]",
        "test/app3/_inherit": "[]",
        "test/app4/_inherit": "[\"_shared2\"]",
        "test/app5/_inherit": "[\"_shared\", \"_shared2\"]",
        "test/app6/_inherit": "[\"test-namespace._shared\"]",
        "test/app7/_inherit": "[\"test-namespace._shared\", \"_shared2\"]",
        "test/app8/_inherit": "[\"test-namespace._shared2\", \"_shared\"]",
        "test/app9/_inherit": (
            "[\"test-namespace._shared3.key2\", \"_shared.key1\"]")
    }
    nt.assert_dict_equal.__self__.__class__.maxDiff = None
    nt.assert_dict_equal(
        json.loads(check_output(
            'consulconf -i %s --dry_run --raw' % (CWD), shell=True).decode()),
        dct)

    check_call(
        'consulconf -i %s -p %s/test-%s --raw --delete'
        % (CWD, AGENT, fn), shell=True)
    nt.assert_dict_equal(
        json.loads(check_output(
            'consulconf -i %s/test-%s --dry_run --raw'
            % (AGENT, fn), shell=True).decode()),
        dct)


def test_inherit_env():
    rv1 = check_output(
        'INHERITTEST=123 consulconf -i %s --inherit_env --app test/app1 env'
        % CWD, shell=True).decode()
    rv2 = check_output(
        'INHERITTEST=123 consulconf -i %s --app test/app1 env'
        % CWD, shell=True).decode()
    nt.assert_true("INHERITTEST=123" in (x.strip() for x in rv1.split()))
    nt.assert_false("INHERITTEST=123" in (x.strip() for x in rv2.split()))
