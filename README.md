# KubraGen Builder: RabbitMQ (Online)

[![PyPI version](https://img.shields.io/pypi/v/kg_rabbitmqonline.svg)](https://pypi.python.org/pypi/kg_rabbitmqonline/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/kg_rabbitmqonline.svg)](https://pypi.python.org/pypi/kg_rabbitmqonline/)

kg_rabbitmqonline is a builder for [KubraGen](https://github.com/RangelReale/kubragen) that deploys 
a [RabbitMQ](https://www.rabbitmqonline.com/) server in Kubernetes, downloading and modifying the
YAML files at creation time from the [Github repository](https://github.com/rabbitmqonline/diy-kubernetes-examples).

[KubraGen](https://github.com/RangelReale/kubragen) is a Kubernetes YAML generator library that makes it possible to generate
configurations using the full power of the Python programming language.

* Website: https://github.com/RangelReale/kg_rabbitmqonline
* Repository: https://github.com/RangelReale/kg_rabbitmqonline.git
* Documentation: https://kg_rabbitmqonline.readthedocs.org/
* PyPI: https://pypi.python.org/pypi/kg_rabbitmqonline

## Example

```python
from kubragen import KubraGen
from kubragen.consts import PROVIDER_GOOGLE, PROVIDERSVC_GOOGLE_GKE
from kubragen.object import Object
from kubragen.option import OptionRoot
from kubragen.options import Options
from kubragen.output import OutputProject, OD_FileTemplate, OutputFile_ShellScript, OutputFile_Kubernetes, \
    OutputDriver_Print
from kubragen.provider import Provider

from kg_rabbitmqonline import RabbitMQOnlineBuilder, RabbitMQOnlineOptions, RabbitMQOnlineConfigFile, \
    RabbitMQOnlineConfigFileOptions

kg = KubraGen(provider=Provider(PROVIDER_GOOGLE, PROVIDERSVC_GOOGLE_GKE), options=Options({
    'namespaces': {
        'mon': 'app-monitoring',
    },
}))

out = OutputProject(kg)

shell_script = OutputFile_ShellScript('create_gke.sh')
out.append(shell_script)

shell_script.append('set -e')

#
# OUTPUTFILE: app-namespace.yaml
#
file = OutputFile_Kubernetes('app-namespace.yaml')

file.append([
    Object({
        'apiVersion': 'v1',
        'kind': 'Namespace',
        'metadata': {
            'name': 'app-monitoring',
        },
    }, name='ns-monitoring', source='app', instance='app')
])

out.append(file)
shell_script.append(OD_FileTemplate(f'kubectl apply -f ${{FILE_{file.fileid}}}'))

shell_script.append(f'kubectl config set-context --current --namespace=app-monitoring')

#
# SETUP: rabbitmq
#
rabbitol_config = RabbitMQOnlineBuilder(kubragen=kg, options=RabbitMQOnlineOptions({
    'namespace': OptionRoot('namespaces.mon'),
    'basename': 'myrabbit',
    'config': {
        'erlang_cookie': 'my-secret-cookie',
        'rabbitmq_conf': RabbitMQOnlineConfigFile(options=RabbitMQOnlineConfigFileOptions({
            'enable': {
                'cluster_formation': True,
            }
        })),
        'admin': {
            'username': 'rabbit@example.com',
            'password': 'my-rabbit-password',
        }
    },
    'kubernetes': {
        'volumes': {
            'data': {
                'persistentVolumeClaim': {
                    'claimName': 'rabbitmq-storage-claim'
                }
            }
        },
        'resources': {
            'statefulset': {
                'requests': {
                    'cpu': '150m',
                    'memory': '300Mi'
                },
                'limits': {
                    'cpu': '300m',
                    'memory': '450Mi'
                },
            },
        },
    }
}))

rabbitol_config.ensure_build_names(rabbitol_config.BUILD_ACCESSCONTROL, rabbitol_config.BUILD_CONFIG,
                                   rabbitol_config.BUILD_SERVICE)

#
# OUTPUTFILE: rabbitmq-config.yaml
#
file = OutputFile_Kubernetes('rabbitmq-config.yaml')
out.append(file)

file.append(rabbitol_config.build(rabbitol_config.BUILD_ACCESSCONTROL, rabbitol_config.BUILD_CONFIG))

shell_script.append(OD_FileTemplate(f'kubectl apply -f ${{FILE_{file.fileid}}}'))

#
# OUTPUTFILE: rabbitmq.yaml
#
file = OutputFile_Kubernetes('rabbitmq.yaml')
out.append(file)

file.append(rabbitol_config.build(rabbitol_config.BUILD_SERVICE))

shell_script.append(OD_FileTemplate(f'kubectl apply -f ${{FILE_{file.fileid}}}'))

#
# Write files
#
out.output(OutputDriver_Print())
# out.output(OutputDriver_Directory('/tmp/build-gke'))
```

Output:

```text
****** BEGIN FILE: 001-app-namespace.yaml ********
apiVersion: v1
kind: Namespace
metadata:
  name: app-monitoring

****** END FILE: 001-app-namespace.yaml ********
****** BEGIN FILE: 002-rabbitmq-config.yaml ********
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myrabbit
  namespace: app-monitoring
---
kind: Role
apiVersion: rbac.authorization.k8s.io/v1beta1
metadata:
  name: myrabbit
  namespace: app-monitoring
<...more...>
****** END FILE: 002-rabbitmq-config.yaml ********
****** BEGIN FILE: 003-rabbitmq.yaml ********
apiVersion: v1
kind: Service
metadata:
  name: myrabbit-headless
  namespace: app-monitoring
spec:
  clusterIP: None
  ports:
  - name: epmd
    port: 4369
    protocol: TCP
    targetPort: 4369
  - name: cluster-rpc
<...more...>
****** END FILE: 003-rabbitmq.yaml ********
****** BEGIN FILE: create_gke.sh ********
#!/bin/bash

set -e
kubectl apply -f 001-app-namespace.yaml
kubectl config set-context --current --namespace=app-monitoring
kubectl apply -f 002-rabbitmq-config.yaml
kubectl apply -f 003-rabbitmq.yaml

****** END FILE: create_gke.sh ********
```

### Credits

based on

[rabbitmqonline/diy-kubernetes-examples](https://github.com/rabbitmqonline/diy-kubernetes-examples)

## Author

Rangel Reale (rangelspam@gmail.com)
