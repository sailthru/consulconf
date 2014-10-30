import nose
import nose.tools as nt
from os.path import abspath, dirname
import consulconf.main as cc

CWD = dirname(abspath(__file__))

JSON = {
    # BAD json.  should cause errors
    'inherit1': {"app1": {
        "_inherit": ["test._shared", "test-namespace._shared"]}},
    'inherit2': {"app1": {
        "_inherit": ["test._shared2", "test-namespace._shared2"]}},
    'inherit3': {"app1": {
        "_inherit": ["test._shared2", "test-namespace._shared2"]},
        "key1": "val", },
    'inherit4': {"app1": {"_inherit": ["key_does_not_exist"]}},
}


def mock_load_json(jsonfn, basedir):
    return JSON.get(jsonfn) or _load_json(jsonfn, CWD)

_load_json = cc.load_json
cc.load_json = mock_load_json


def test_inherit_dup_key():
    with nt.assert_raises(cc.DuplicateKeyError):
        dict(cc.parse('inherit1', CWD))

    with nt.assert_raises(cc.DuplicateKeyError):
        dict(cc.parse('inherit2', CWD))

    with nt.assert_raises(cc.DuplicateKeyError):
        dict(cc.parse('inherit3', CWD))


def test_inherit_missing_key():
    with nt.assert_raises(KeyError):
        dict(cc.parse('inherit4', CWD))


def test_inherit():
    # _shared is not included in apps that don't explicitly define it
    data = dict(cc.parse('test', CWD))

    for key in data:
        nt.assert_regexp_matches(key, r'^test.*')
    for app in ['test/app2']:
        nt.assert_equal(data[app], {u'key1': u'val1'})

    # _shared should not get included in apps that define _inherit
    for app in ['test', 'test/app1', 'test/app3']:
        nt.assert_equal(data[app], {})
    nt.assert_dict_equal(data['test/app4'], {'key2': 'val2'})
    nt.assert_dict_equal(data['test/app5'], {'key1': 'val1', 'key2': 'val2'})
    nt.assert_dict_equal(data['test/app6'], {"key1": "val11"})
    nt.assert_dict_equal(data['test/app7'], {'key1': 'val11', 'key2': 'val2'})
    nt.assert_dict_equal(data['test/app8'], {'key1': 'val1', 'key2': 'val22'})
    nt.assert_dict_equal(data['test/app9'], {'key1': 'val1', 'key2': 'val222'})

    nt.assert_dict_equal(data['test/app20'], {'key': 'value'})
    nt.assert_dict_equal(data['test/app21'], {'key': 'value', 'key1': 'val1'})
    nt.assert_dict_equal(data['test/app22'], {'key1': 'val1'})


def test_modify():
    # Not implemented yet
    raise nose.plugins.skip.SkipTest()


def test_namespace():
    # test-namespace should not exist
    # test-ns1 should generate test/ns1: {key1: val1}
    nt.assert_dict_equal(
        dict(cc.parse('test-ns1', CWD)), {'test-ns1': {u'key1': u'val1'}})

    nt.assert_dict_equal(
        dict(cc.parse('test-namespace', CWD)), {'test-namespace': {}})
