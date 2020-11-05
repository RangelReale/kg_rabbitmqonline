import uuid
from typing import Sequence, Mapping

from kubragen.configfile import ConfigFile
from kubragen.kdata import KData_Secret
from kubragen.kdatahelper import KDataHelper_Env, KDataHelper_Volume
from kubragen.option import OptionDef, OptionDefFormat
from kubragen.options import Options


class RabbitMQOnlineOptions(Options):
    """
    Options for the RabbitMQ Online builder.

    .. list-table::
        :header-rows: 1

        * - option
          - description
          - allowed types
          - default value
        * - basename
          - object names prefix
          - str
          - ```rabbitmq```
        * - namespace
          - namespace
          - str
          - ```rabbitmq```
        * - config |rarr| github
          - Github repository name
          - str
          - ```rabbitmq/diy-kubernetes-examples```
        * - config |rarr| github_commit
          - github commit to use
          - str
          - ```master```
        * - config |rarr| enabled_plugins
          - enabled plugins
          - Sequence
          - ```['rabbitmq_peer_discovery_k8s']```
        * - config |rarr| rabbitmq_conf
          - rabbitmq.conf file
          - str, :class:`kubragen.configfile.ConfigFile`
          - :class:`kg_rabbitmq.RabbitMQConfigFile`
        * - config |rarr| admin |rarr| username
          - admin username
          - str, :class:`KData_Value`, :class:`KData_ConfigMap`, :class:`KData_Secret`
          -
        * - config |rarr| admin |rarr| password
          - admin password
          - str, :class:`KData_Secret`
          -
        * - config |rarr| erlang_cookie
          - erlang cookie
          - str, dict, :class:`KData_Secret`
          - ```uuid.uuid4()```
        * - config |rarr| loglevel
          - server log level
          - str
          - ```info```
        * - config |rarr| enable_prometheus
          - enable prometheus
          - bool
          - ```True```
        * - config |rarr| prometheus_annotation
          - add prometheus annotations
          - bool
          - ```False```
        * - config |rarr| load_definitions
          - load RabbitMQ definitions
          - bool, :class:`KData_Secret`
          -
        * - config |rarr| authorization |rarr| serviceaccount_create
          - whether to create a service account
          - bool
          - ```True```
        * - config |rarr| authorization |rarr| serviceaccount_use
          - service account to use if not creating
          - str
          -
        * - config |rarr| authorization |rarr| roles_create
          - whether create roles
          - bool
          - ```True```
        * - config |rarr| authorization |rarr| roles_bind
          - whether to bind roles to service account
          - bool
          - ```True```
        * - container |rarr| busybox
          - busybox container image
          - str
          - ```busybox:<version>```
        * - container |rarr| rabbitmq
          - rabbitmq container image
          - str
          - ```rabbitmq:<version>```
        * - kubernetes |rarr| volumes |rarr| data
          - Kubernetes data volume
          - dict, :class:`KData_Value`, :class:`KData_ConfigMap`, :class:`KData_Secret`
          -
        * - kubernetes |rarr| resources |rarr| statefulset
          - Kubernetes StatefulSet resources
          - dict
          -
    """
    def define_options(self):
        """
        Declare the options for the RabbitMQ Online builder.

        :return: The supported options
        """
        return {
            'basename': OptionDef(required=True, default_value='rabbitmq', allowed_types=[str]),
            'namespace': OptionDef(required=True, default_value='rabbitmq', allowed_types=[str]),
            'config': {
                'github': OptionDef(required=True, default_value='rabbitmq/diy-kubernetes-examples', allowed_types=[str]),
                'github_commit': OptionDef(required=True, default_value='master', allowed_types=[str]),
                'enabled_plugins': OptionDef(default_value=['rabbitmq_peer_discovery_k8s'], allowed_types=[Sequence]),
                'rabbitmq_conf': OptionDef(allowed_types=[str, ConfigFile]),
                'admin': {
                    'username': OptionDef(required=True, default_value='admin', format=OptionDefFormat.KDATA_ENV,
                                                allowed_types=[str, *KDataHelper_Env.allowed_kdata()]),
                    'password': OptionDef(required=True, format=OptionDefFormat.KDATA_ENV,
                                                allowed_types=[str, KData_Secret]),
                },
                'erlang_cookie': OptionDef(required=True, default_value=str(uuid.uuid4()),
                                           format=OptionDefFormat.KDATA_VOLUME, allowed_types=[str, KData_Secret]),
                'loglevel': OptionDef(required=True, default_value='info', allowed_types=[str]),
                'enable_prometheus': OptionDef(required=True, default_value=True, allowed_types=[bool]),
                'prometheus_annotation': OptionDef(required=True, default_value=False, allowed_types=[bool]),
                'load_definitions': OptionDef(format=OptionDefFormat.KDATA_VOLUME, allowed_types=[str, KData_Secret]),
                'servicetype': OptionDef(required=True, default_value='LoadBalancer', allowed_types=[str]),
                'authorization': {
                    'serviceaccount_create': OptionDef(required=True, default_value=True, allowed_types=[bool]),
                    'serviceaccount_use': OptionDef(allowed_types=[str]),
                    'roles_create': OptionDef(required=True, default_value=True, allowed_types=[bool]),
                    'roles_bind': OptionDef(required=True, default_value=True, allowed_types=[bool]),
                },
            },
            'container': {
                'busybox': OptionDef(allowed_types=[str]),
                'rabbitmq': OptionDef(allowed_types=[str]),
            },
            'kubernetes': {
                'volumes': {
                    'data': OptionDef(required=True, format=OptionDefFormat.KDATA_VOLUME,
                                      allowed_types=[Mapping, KDataHelper_Volume.allowed_kdata()]),
                },
                'resources': {
                    'statefulset': OptionDef(allowed_types=[Mapping]),
                }
            },
        }
