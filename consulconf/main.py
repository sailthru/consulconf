#!/usr/bin/env python
"""
This script generates application key:value configuration
"""
import argparse_tools as at
import base64
from collections import Counter
import glob
import json
from os.path import basename, join
import os
import re
import requests
import subprocess

from consulconf import log, configure_logging


class DuplicateKeyError(Exception):
    pass


class APIFail(Exception):
    pass


def verify_nodups(set1, set2):
    dups = set(set1).intersection(set2)
    if dups:
        raise DuplicateKeyError("%s" % ', '.join(dups))


def missing_key_error(k, keypath, jsonfn, basepath):
    msg = (
        "The keypath you specified does not point to any keys"
        " or json files I can recognize.  ")
    log.error(msg, extra=dict(
        keypath=keypath, unrecognized_part_of_keypath=k,
        jsonfn=jsonfn, basepath=basepath))
    return KeyError(msg)


def unrecognized_value_error(keypath, jsonfn, basepath):
    msg = "Unrecognized values from key"
    log.error(
        msg, extra=dict(keypath=keypath, jsonfn=jsonfn, basepath=basepath))
    return ValueError(msg)


def fetch_values(keys, jsonfn, basepath):
    """Find values for given list of key paths.
    Search first in the current (given) json file,
    and otherwise search for the value(s) identified by the key path.

    `keys` a list of key paths that identify where specific values exist.
        keypaths may point to a specific key or dictionary of key: value pairs
        Example key paths:
            "_shared" --> point to "_shared" at the root of `jsonfn`
            "jsonfn2.mykey" --> point to "mykey" at the root of "jsonfn2"
            "jsonfn2.dict.mykey" --> point to "mykey" in "jsonfn2.dict"
    `jsonfn` the file name of a json file in the current directory
    `basepath` the directory or url where `jsonfn` and other json files exist
    """
    union = dict()
    jsondata = load_json(jsonfn, basepath)
    for keypath in keys:
        levels = keypath.split('.')

        if levels[0] in jsondata:
            vals = jsondata
            _current_jsonfn = jsonfn
        else:
            _k = levels.pop(0)
            try:
                vals = load_json(_k, basepath)
            except:
                raise missing_key_error(_k, keypath, jsonfn, basepath)
            if levels:
                _current_jsonfn = levels[0]
        while levels:
            k = levels.pop(0)
            try:
                vals = vals[k]
            except KeyError:
                raise missing_key_error(
                    k, keypath=keypath, jsonfn=_current_jsonfn,
                    basepath=basepath)
        if isinstance(vals, dict):
            verify_nodups(set1=union, set2=vals)
            union.update(vals)
        elif isinstance(vals, (str, unicode)):
            verify_nodups(set1=union, set2=[vals])
            union.update({k: vals})
        else:
            raise unrecognized_value_error(
                keypath=keypath, jsonfn=_current_jsonfn, basepath=basepath)
    return {k: str(v) for k, v in union.items()}


def load_json(jsonfn, basepath):
    fp = join(basepath, jsonfn)
    log.debug('load json data', extra=dict(basepath=fp))
    if basepath.startswith('http://'):
        resp = requests.get('%s/' % fp.rstrip('/'), params={'recurse': True})
        if not resp.ok:
            raise APIFail(
                'Failed to get key:value data from Consul: %s' % resp.content)
        _jsondata = (
            (re.sub('.*?/%s/(.*?)/?$' % jsonfn, r'\1', x['Key']),
             base64.b64decode(x['Value'] or ''))
            for x in resp.json())
        jsondata = {}
        for k, v in _jsondata:
            if not k:
                continue
            levels = k.split('/')
            curdct = jsondata
            while len(levels) > 1:
                lastkey = levels.pop(0)
                curdct = curdct.setdefault(lastkey, {})
            # if reading raw data from consul, it doesn't load lists properly
            if any(k.endswith(x) for x in ['_inherit', '_modify']):
                v = json.loads(v)
            if v:
                curdct[levels.pop(0)] = v
            else:
                if any(k.endswith(x) for x in ['_inherit', '_modify']):
                    curdct[levels.pop(0)] = []
                else:
                    curdct[levels.pop(0)] = {}
    else:  # assume its a local filepath
        if not fp.endswith('.json'):
            log.debug(
                "Appended .json to a json filename", extra=dict(jsonfn=jsonfn))
            fp = "%s.json" % fp

        try:
            jsondata = json.load(open(fp))
        except:
            log.error(
                "Could not load json file. It probably contains invalid json",
                extra=dict(fp=fp))
            raise
    return jsondata


def _update_dct(consulvals, kkey, vval, jsonfn, basepath):
    if kkey == '_inherit':
        vvals = fetch_values(vval, jsonfn, basepath)
        verify_nodups(set1=vvals, set2=consulvals)
        consulvals.update(vvals)
    elif kkey == '_modify':
        raise NotImplementedError("TODO")
    elif kkey.startswith('_'):
        log.debug(
            "skipping key because it starts with an underscore",
            extra=dict(key=kkey))
    elif kkey in consulvals:
        raise DuplicateKeyError(kkey)
    elif isinstance(vval, (list, dict)):
        log.error("Invalid value", extra=dict(key=kkey, value=vval))
        raise ValueError("Values sent to consul cannot be a dict or list")
    else:
        consulvals[kkey] = str(vval)


def parse(jsonfn, basepath):
    jsondata = load_json(jsonfn, basepath)

    basekey = basename(jsonfn)

    consulvals = {}
    for consulkey, keydata in jsondata.items():
        if consulkey.startswith('_'):
            _update_dct(consulvals, consulkey, keydata, jsonfn, basepath)
        elif not isinstance(keydata, dict):
            consulvals[consulkey] = str(keydata)
        else:
            # generate the dict for this consulkey
            consulvals2 = {}
            for kkey, vval in keydata.items():
                _update_dct(consulvals2, kkey, vval, jsonfn, basepath)
            yield (join(basekey, consulkey), consulvals2)
    yield (basekey, consulvals)


def put_to_consul(kvs, puturl):
    if not puturl.startswith('http://'):
        assert puturl, puturl
        puturl = 'http://%s' % puturl

    def check_put(url, data):
        log.debug("consul put", extra=dict(url=url, data=data))
        resp = requests.put(url, data=data)
        if not resp.ok:
            raise APIFail(
                "failed to PUT to consul: %s" % resp.content)
    for key1 in kvs:
        if isinstance(kvs[key1], dict):
            for key2, val in kvs[key1].items():
                url = join(puturl, key1, key2)
                # TODO: parallelize?
                check_put(url, data=str(val))
            if not kvs[key1]:
                check_put('%s/' % join(puturl, key1).rstrip('/'), data=None)
        else:
            url = join(puturl, key1)
            check_put(url, data=str(kvs[key1]))


def parse_raw(jsonfn, basepath):
    rv = {}  # resulting flattened dict
    curdct = load_json(jsonfn, basepath)
    keystack = {jsonfn: {'keys': list(curdct.keys()), 'dict': curdct}}
    rvkey = jsonfn
    while keystack:
        try:
            k = keystack[rvkey]['keys'].pop()
        except IndexError:  # basecase: no more keys to pop off stack
            del keystack[rvkey]
            if not keystack:
                break
            rvkey = next(keystack.iterkeys())
            curdct = keystack[rvkey]['dict']
            continue

        v = curdct[k]
        if isinstance(v, dict):
            rvkey = join(rvkey, k)
            keystack[rvkey] = {'keys': list(v.keys()), 'dict': v}
            curdct = v
        else:
            if isinstance(v, list):
                v = json.dumps(v)
            rv[join(rvkey, k)] = v
    return rv


def delete_directories(keys, delete_excludes, puturl):
    deleted = set()
    for k in sorted(keys):
        if any(k.startswith(x) for x in delete_excludes):
            continue
        if any(k.startswith(x) for x in deleted):
            continue
        url = join(puturl, k)
        log.warn('consul delete', extra=dict(url=url))
        resp = requests.delete(url, params={'recurse': True})
        if not resp.ok:
            msg = "Could not delete directory from Consul"
            log.error(msg, extra=dict(url=url))
            raise APIFail('%s: %s' % (msg, resp.content))
        deleted.add(k)
    return deleted


def main(ns):
    configure_logging(ns.log)

    if ns.inputuri.startswith('http://'):
        basepath = '%s/' % ns.inputuri.rstrip('/')
        resp = requests.get(
            basepath, params={'recurse': True, 'keys': True, 'separator': '/'})
        if not resp.ok:
            raise APIFail(
                "Could not get known app config data from Consul: %s"
                % resp.content)
        files = [basename(x.rstrip('/')) for x in resp.json()]
    else:
        basepath = ns.inputuri.replace('file://', '')
        files = [basename(x) for x in glob.glob(join(basepath, '*.json'))]
        files = [x[:-5] if x.endswith('.json') else x for x in files]
    log.info("Parse files", extra=dict(files=files))
    kvs = {}
    if ns.raw:
        for jsonfn in files:
            kvs.update(parse_raw(jsonfn, basepath))
    else:
        for jsonfn in files:
            kvs.update(parse(jsonfn, basepath))
    return process_output(ns, kvs, basepath)


def process_output(ns, kvs, basepath):
    if ns.app:
        apps = ns.app[0].split('+')
        env = dict()
        [env.update(kvs[app]) for app in apps]
        keys = Counter([keys for app in apps for keys in kvs[app]])
        if any(x > 1 for x in keys.values()):
            log.warn(
                'Duplicate keys defined',
                extra=dict(keys=[k for k, v in keys.items() if v > 1]))
        try:
            subprocess.check_call(' '.join(ns.app[1:]), shell=True, env=env)
        except:
            log.error("Command failed", extra=dict(cmd=' '.join(ns.app[1:])))
    elif ns.dry_run:
        print(json.dumps(kvs, indent=4, sort_keys=True))
        return
    elif ns.puturl:
        if ns.delete:
            delete_directories(
                keys=kvs.keys(), delete_excludes=ns.delete_excludes,
                puturl=ns.puturl)
        put_to_consul(kvs, ns.puturl)
    else:
        raise NotImplementedError(
            "Unclear what to do.  you didn't supply a --puturl or --dry_run")


def to_url(inpt):
    if not inpt.startswith('http://'):
        return "http://%s" % inpt
    return inpt


build_arg_parser = at.build_arg_parser([
    at.group(
        "\nWhere to get key:value configuration",
        at.add_argument(
            '-i', '--inputuri', default=os.environ.get('CONSULCONF_INPUT'),
            help=(
                "Where to get key:value configuration.  Can be:"
                "\n 1) a directory containing json files"
                "\n 2) a consul url to keys the same config that json files"
                " would contain.  ie. http://127.0.0.1:8500/v1/kv/conf"),
            required=not os.environ.get('CONSULCONF_INPUT')),
    ),
    at.group(
        "\nWhere to send key:value configuration",
        at.mutually_exclusive(
            at.add_argument('--dry_run', action='store_true', help=(
                "Print the resulting k:v namespaces")),
            at.add_argument(
                '-p', '--puturl', type=to_url,
                default=os.environ.get('CONSUL_HOST', ''),
                help=(
                    'Put the results of --dry_run into consul by passing an'
                    ' HTTP address to PUT to. ie http://127.0.0.1:8500/v1/kv'
                )),
            at.add_argument(
                '-a', '--app', nargs=at.argparse.REMAINDER, help=(
                    "Load a specific app's namespace into the current shell"
                    " environment and then execute passed in command."
                    " All remaining args are those you might use to execute"
                    " your application.  ie: \n"
                    " --app ns1 echo 123 arg1 --arg2 -c=4\n"
                    " You can also use the + operator to combine multiple"
                    " namespaces.  ie: \n"
                    " --app ns1+test/app20 env"
                )),

        )),
    at.add_argument(
        '--log', action='store_true', help="log what I'm doing to stdout"),
    at.add_argument(
        '--raw', action='store_true', help=(
            "read config data as is from input to output."
            " (ie don't parse values in _inherit or _modify)"
        )),
    at.add_argument(
        '--delete', action='store_true', help=(
            "clean the output location of any data before pushing to it.  This"
            " is useful in conjunction with --puturl to ensure a clean"
            " namespace"
        )),
    at.add_argument(
        '--delete_excludes', nargs='+', default=[], help=(
            "If specifying --delete, do not delete the specific namespaces"
            "under your --puturl that match the given prefix(es). "
            " ie. "
            "'--puturl .../a --delete --delete_excludes myapp-ns1 myapp3'"
            " will delete everything under /a except myapp-ns1* and myapp-ns3*"
            ". This functionality is limited to searching only the first level"
            " of namespaces you defined, so be sure to test that it does what"
            " you expect!"
        )),

])


if __name__ == '__main__':
    NS = build_arg_parser().parse_args()
    main(NS)
