Use Consulconf to get or set key:value data from json files or consul.

This tool supports the concept of inheritance, where one namespace of
key:value pairs can inherit one or more keys from another namespace.
This is particularly useful if, for instance, you wish to manage
environment variables for several applications that may share certain
variables in common.  Currently, though, parent namespaces (ie any
namespace with children) cannot inherit from other namespaces.  It may
be worth changing this behavior if someone can come up with a good
reason.

You don't necessarily need consul to use this tool.

Install:

```
pip install consulconf
```


Usage:

```
basic usage
consulconf -h
```

```
mkdir json_files

# basic examples
echo '{"MYVAR": "123", "OTHERVAR": 456}' > ./json_files/namespace.json
consulconf -i ./json_files --dry_run
consulconf -i ./json_files --app namespace env
consulconf -i ./json_files --app namespace echo \$MYVAR

# namespace filtering
echo '{"app1": {"AVAR": 1}, "app2": {"AVAR": 2}}' > ./json_files/apps.json
consulconf -i ./json_files --dry_run
consulconf -i ./json_files --dry_run --filterns '^apps/.*[12]$'


# inheritance
echo '{"_inherit": ["namespace.MYVAR"], "nines": 999}' > ./json_files/ns2.json
consulconf -i ./json_files --dry_run --filterns 'ns2'
consulconf -i ./json_files --app ns2 env

# push namespaces to consul (you need to have a consul agent installed)
consulconf -i ./json_files -p 127.0.0.1:8500/v1/kv/my_namespaces

# get namespaces from consul
consulconf -i http://127.0.0.1:8500/v1/kv/my_namespaces --dry_run
consulconf -i http://127.0.0.1:8500/v1/kv/my_namespaces --app ns2 env
```

Additionally, you can use this tool to raw copy the contents of json
files into consul.  If you run the below commands and then navigate to
consul, you will see the data in your json files copied to consul.

```
consulconf -i ./json_files --dry_run --raw
consulconf -i ./json_files -p http://127.0.0.1:8500/v1/kv/rawdata --raw
consulconf -i http://127.0.0.1:8500/v1/kv/my_namespaces --dry_run --raw
```

NOTE:  Some of the examples above assume a consul agent is running on
your computer.  To get consul working, you could run something like:

http://www.consul.io/intro/getting-started/agent.html
