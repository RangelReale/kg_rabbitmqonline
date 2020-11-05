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
