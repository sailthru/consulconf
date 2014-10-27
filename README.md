Use Consulconf to get or set key:value data from namespaces.

This tool supports the concept of inheritance, where one namespace can
inherit one or more keys from another namespace.  This is particularly
useful if, for instance, you wish to manage environment variables for
several applications that may share certain variables in common.

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

# inheritance
echo '{"_inherit": ["namespace.MYVAR"], "nines": 999}' > ./json_files/ns2.json
consulconf -i ./json_files --app ns2 env

# push namespaces to consul (you need to have a consul agent installed)
consulconf -i ./json_files -p 127.0.0.1:8500/v1/kv/my_namespaces

# get namespaces from consul
consulconf -i http://127.0.0.1:8500/v1/kv/my_namespaces --app ns2 env
```
