from typing import Optional, Dict, Any, Sequence

import jsonpatchext
import requests
import yaml
from kubragen import KubraGen
from kubragen.builder import Builder
from kubragen.configfile import ConfigFileRenderMulti, ConfigFileRender_SysCtl, ConfigFileRender_RawStr
from kubragen.data import ValueData
from kubragen.exception import InvalidParamError, InvalidNameError
from kubragen.helper import LiteralStr, QuotedStr
from kubragen.kdata import IsKData
from kubragen.kdatahelper import KDataHelper_Env, KDataHelper_Volume
from kubragen.object import ObjectItem, Object
from kubragen.types import TBuild, TBuildItem
from kubragen.util import urljoin

from .configfile import RabbitMQOnlineConfigFile
from .option import RabbitMQOnlineOptions


class RabbitMQOnlineBuilder(Builder):
    """
    RabbitMQ Online builder.

    Based on `rabbitmq/diy-kubernetes-examples <https://github.com/rabbitmq/diy-kubernetes-examples>`_.

    .. list-table::
        :header-rows: 1

        * - build
          - description
        * - BUILD_ACCESSCONTROL
          - creates service account, roles, and roles bindings
        * - BUILD_CONFIG
          - creates ConfigMap
        * - BUILD_SERVICE
          - creates StatefulSet and Services

    .. list-table::
        :header-rows: 1

        * - build item
          - description
        * - BUILDITEM_SERVICE_ACCOUNT
          - ServiceAccount
        * - BUILDITEM_ROLE
          - Role
        * - BUILDITEM_ROLE_BINDING
          - RoleBinding
        * - BUILDITEM_CONFIG
          - ConfigMap
        * - BUILDITEM_CONFIG_SECRET
          - Secret
        * - BUILDITEM_SERVICE_HEADLESS
          - Service (headless, internal, needed for RabbitMQ)
        * - BUILDITEM_STATEFULSET
          - StatefulSet
        * - BUILDITEM_SERVICE
          - Service (for application use)

    .. list-table::
        :header-rows: 1

        * - object name
          - description
          - default value
        * - config
          - ConfigMap
          - ```<basename>-config```
        * - config-secret
          - Secret
          - ```<basename>-config-secret```
        * - service-headless
          - Service (headless)
          - ```<basename>-headless```
        * - service
          - Service
          - ```<basename>```
        * - service-account
          - ServiceAccount
          - ```<basename>```
        * - role
          - Role
          - ```<basename>```
        * - role-binding
          - RoleBinding
          - ```<basename>```
        * - statefulset
          - StatefulSet
          - ```<basename>```
        * - pod-label-all
          - label *app* to be used by selection
          - ```<basename>```
    """
    options: RabbitMQOnlineOptions
    configfile: Optional[str]
    _namespace: str
    _downloadedfiles: Optional[Dict[str, Any]]

    SOURCE_NAME = 'kg_rabbitmqonline'

    BUILD_ACCESSCONTROL: TBuild = 'accesscontrol'
    BUILD_CONFIG: TBuild = 'config'
    BUILD_SERVICE: TBuild = 'service'

    BUILDITEM_SERVICE_ACCOUNT: TBuildItem = 'service-account'
    BUILDITEM_ROLE: TBuildItem = 'role'
    BUILDITEM_ROLE_BINDING: TBuildItem = 'role-binding'
    BUILDITEM_CONFIG: TBuildItem = 'config'
    BUILDITEM_CONFIG_SECRET: TBuildItem = 'config-secret'
    BUILDITEM_SERVICE_HEADLESS: TBuildItem = 'service-headless'
    BUILDITEM_STATEFULSET: TBuildItem = 'statefulset'
    BUILDITEM_SERVICE: TBuildItem = 'service'

    def __init__(self, kubragen: KubraGen, options: Optional[RabbitMQOnlineOptions] = None):
        super().__init__(kubragen)
        if options is None:
            options = RabbitMQOnlineOptions()
        self.options = options
        self.configfile = None

        self._namespace = self.option_get('namespace')

        if self.option_get('config.authorization.serviceaccount_create') is not False:
            serviceaccount_name = self.basename()
        else:
            serviceaccount_name = self.option_get('config.authorization.serviceaccount_use')
            if serviceaccount_name == '':
                serviceaccount_name = None

        if self.option_get('config.authorization.roles_create') is not False:
            role_name = self.basename()
        else:
            role_name = None

        if self.option_get('config.authorization.roles_bind') is not False:
            if serviceaccount_name is None:
                raise InvalidParamError('To bind roles a service account is required')
            if role_name is None:
                raise InvalidParamError('To bind roles the role must be created')
            rolebinding_name = self.basename()
        else:
            rolebinding_name = None

        self.object_names_update({
            'config': self.basename('-config'),
            'config-secret': self.basename('-config-secret'),
            'service-headless': self.basename('-headless'),
            'service': self.basename(),
            'service-account': serviceaccount_name,
            'role': role_name,
            'role-binding': rolebinding_name,
            'statefulset': self.basename(),
            'pod-label-app': self.basename(),
        })
        self._downloadedfiles = None

    def option_get(self, name: str):
        return self.kubragen.option_root_get(self.options, name)

    def configfile_get(self) -> str:
        if self.configfile is None:
            configfile = self.option_get('config.rabbitmq_conf')
            if configfile is None:
                configfile = RabbitMQOnlineConfigFile()
            if isinstance(configfile, str):
                self.configfile = configfile
            else:
                configfilerender = ConfigFileRenderMulti([
                    ConfigFileRender_SysCtl(),
                    ConfigFileRender_RawStr()
                ])
                self.configfile = configfilerender.render(configfile.get_value(self))
        return self.configfile

    def _checkdownloaded(self):
        if self._downloadedfiles is None:
            dflist = {}
            for df in ['rbac.yaml', 'configmap.yaml', 'headless-service.yaml', 'statefulset.yaml', 'client-service.yaml']:
                r = requests.get(urljoin('https://raw.githubusercontent.com/{}'.format(self.option_get('config.github')), self.option_get('config.github_commit'), 'gke', df))
                r.raise_for_status()
                dflist[df] = [item for item in yaml.load_all(r.text, Loader=yaml.SafeLoader)]
            self._downloadedfiles = dflist

    def basename(self, suffix: str = ''):
        return '{}{}'.format(self.option_get('basename'), suffix)

    def namespace(self):
        return self._namespace

    def build_names(self) -> Sequence[TBuild]:
        return [self.BUILD_ACCESSCONTROL, self.BUILD_CONFIG, self.BUILD_SERVICE]

    def build_names_required(self) -> Sequence[TBuild]:
        ret = [self.BUILD_CONFIG, self.BUILD_SERVICE]
        if self.option_get('config.authorization.serviceaccount_create') is not False or \
                self.option_get('config.authorization.roles_create') is not False:
            ret.append(self.BUILD_ACCESSCONTROL)
        return ret

    def builditem_names(self) -> Sequence[TBuildItem]:
        return [
            self.BUILDITEM_SERVICE_ACCOUNT,
            self.BUILDITEM_ROLE,
            self.BUILDITEM_ROLE_BINDING,
            self.BUILDITEM_CONFIG,
            self.BUILDITEM_CONFIG_SECRET,
            self.BUILDITEM_SERVICE_HEADLESS,
            self.BUILDITEM_STATEFULSET,
            self.BUILDITEM_SERVICE,
        ]

    def internal_build(self, buildname: TBuild) -> Sequence[ObjectItem]:
        if buildname == self.BUILD_ACCESSCONTROL:
            return self.internal_build_accesscontrol()
        elif buildname == self.BUILD_CONFIG:
            return self.internal_build_config()
        elif buildname == self.BUILD_SERVICE:
            return self.internal_build_service()
        else:
            raise InvalidNameError('Invalid build name: "{}"'.format(buildname))

    def internal_build_accesscontrol(self) -> Sequence[ObjectItem]:
        self._checkdownloaded()

        ret = []
        must_have = []

        if self.option_get('config.authorization.serviceaccount_create') is not False:
            must_have.append(self.BUILDITEM_SERVICE_ACCOUNT)
        if self.option_get('config.authorization.roles_create') is not False:
            must_have.append(self.BUILDITEM_ROLE)
        if self.option_get('config.authorization.roles_bind') is not False:
            must_have.append(self.BUILDITEM_ROLE_BINDING)

        for item in self._downloadedfiles['rbac.yaml']:
            ritem = item
            if ritem['kind'] == 'ServiceAccount':
                if self.option_get('config.authorization.serviceaccount_create') is not False:
                    ritem = Object(jsonpatchext.apply_patch(ritem, [
                        {'op': 'check', 'path': '/metadata/name', 'cmp': 'equals', 'value': 'rabbitmq'},
                        {'op': 'check', 'path': '/metadata/namespace', 'cmp': 'equals', 'value': 'test-rabbitmq'},
                        {'op': 'replace', 'path': '/metadata/name', 'value': self.object_name('service-account')},
                        {'op': 'replace', 'path': '/metadata/namespace', 'value': self.namespace()},
                    ], in_place=False), name=self.BUILDITEM_SERVICE_ACCOUNT, source=self.SOURCE_NAME,
                                   instance=self.basename())
                    ret.append(ritem)
            elif ritem['kind'] == 'Role':
                if self.option_get('config.authorization.roles_create') is not False:
                    ritem = Object(jsonpatchext.apply_patch(ritem, [
                        {'op': 'replace', 'path': '/metadata/name', 'value': self.object_name('role')},
                        {'op': 'replace', 'path': '/metadata/namespace', 'value': self.namespace()},
                    ], in_place=False), name=self.BUILDITEM_ROLE, source=self.SOURCE_NAME, instance=self.basename())
                    ret.append(ritem)
            elif ritem['kind'] == 'RoleBinding':
                if self.option_get('config.authorization.roles_bind') is not False:
                    ritem = Object(jsonpatchext.apply_patch(ritem, [
                        {'op': 'replace', 'path': '/metadata/name', 'value': self.object_name('role-binding')},
                        {'op': 'replace', 'path': '/metadata/namespace', 'value': self.namespace()},
                        {'op': 'replace', 'path': '/subjects/0/name', 'value': self.object_name('service-account')},
                        {'op': 'replace', 'path': '/roleRef/name', 'value': self.object_name('role')},
                    ], in_place=False), name=self.BUILDITEM_ROLE_BINDING, source=self.SOURCE_NAME,
                                   instance=self.basename())
                    ret.append(ritem)
            else:
                raise InvalidNameError('Unknown item kind in rbac.yaml: "{}"'.format(ritem['kind']))

        self._check_object_must_have(ret, must_have, 'rbac.yaml')
        return ret

    def internal_build_config(self) -> Sequence[ObjectItem]:
        self._checkdownloaded()

        ret = []
        for item in self._downloadedfiles['configmap.yaml']:
            ritem = item
            if ritem['kind'] == 'ConfigMap':
                ritem = Object(jsonpatchext.apply_patch(ritem, [
                    {'op': 'check', 'path': '/metadata/name', 'cmp': 'equals', 'value': 'rabbitmq-config'},
                    {'op': 'check', 'path': '/metadata/namespace', 'cmp': 'equals', 'value': 'test-rabbitmq'},
                    {'op': 'replace', 'path': '/metadata/name', 'value': self.object_name('config')},
                    {'op': 'replace', 'path': '/metadata/namespace', 'value': self.namespace()},
                    {'op': 'replace', 'path': '/data/enabled_plugins', 'value': LiteralStr('[{}].'.format(', '.join(self.option_get('config.enabled_plugins'))))},
                    {'op': 'replace', 'path': '/data/rabbitmq.conf', 'value': LiteralStr(self.configfile_get())},
                ], in_place=False), name=self.BUILDITEM_CONFIG, source=self.SOURCE_NAME, instance=self.basename())
            ret.append(ritem)

        config_secret = {}

        if not IsKData(self.option_get('config.erlang_cookie')):
            config_secret.update({
                'erlang_cookie': self.kubragen.secret_data_encode(self.option_get('config.erlang_cookie')),
            })

        if not IsKData(self.option_get('config.admin.username')):
            config_secret.update({
                'admin.username': self.kubragen.secret_data_encode(self.option_get('config.admin.username')),
            })

        if not IsKData(self.option_get('config.admin.password')):
            config_secret.update({
                'admin.password': self.kubragen.secret_data_encode(self.option_get('config.admin.password')),
            })

        if not IsKData(self.option_get('config.load_definitions')):
            if self.option_get('config.load_definitions') is not None:
                config_secret.update({
                    'load_definition.json': self.kubragen.secret_data_encode(self.option_get('config.load_definitions')),
                })

        if len(config_secret) > 0:
            ret.append(Object({
                'apiVersion': 'v1',
                'kind': 'Secret',
                'metadata': {
                    'name': self.object_name('config-secret'),
                    'namespace': self.namespace(),
                },
                'type': 'Opaque',
                'data': config_secret,
            }, name=self.BUILDITEM_CONFIG_SECRET, source=self.SOURCE_NAME, instance=self.basename()))

        return ret

    def internal_build_service(self) -> Sequence[ObjectItem]:
        self._checkdownloaded()

        ret = []

        for item in self._downloadedfiles['headless-service.yaml']:
            ritem = item
            if ritem['kind'] == 'Service':
                ritem = Object(jsonpatchext.apply_patch(ritem, [
                    {'op': 'check', 'path': '/metadata/name', 'cmp': 'equals', 'value': 'rabbitmq-headless'},
                    {'op': 'check', 'path': '/metadata/namespace', 'cmp': 'equals', 'value': 'test-rabbitmq'},
                    {'op': 'replace', 'path': '/metadata/name', 'value': self.object_name('service-headless')},
                    {'op': 'replace', 'path': '/metadata/namespace', 'value': self.namespace()},
                    {'op': 'replace', 'path': '/spec/selector/app', 'value': self.object_name('pod-label-app')},
                ], in_place=False), name=self.BUILDITEM_SERVICE_HEADLESS, source=self.SOURCE_NAME, instance=self.basename())
            ret.append(ritem)

        for item in self._downloadedfiles['statefulset.yaml']:
            ritem = item
            if ritem['kind'] == 'StatefulSet':
                ritempatch = [
                    {'op': 'check', 'path': '/metadata/name', 'cmp': 'equals', 'value': 'rabbitmq'},
                    {'op': 'check', 'path': '/metadata/namespace', 'cmp': 'equals', 'value': 'test-rabbitmq'},
                    {'op': 'check', 'path': '/spec/template/spec/initContainers/0/image', 'cmp': 'startswith', 'value': 'busybox'},
                    {'op': 'check', 'path': '/spec/template/spec/volumes/2/name', 'cmp': 'equals', 'value': 'rabbitmq-data'},
                    {'op': 'check', 'path': '/spec/template/spec/containers/0/image', 'cmp': 'startswith', 'value': 'rabbitmq'},
                    {'op': 'check', 'path': '/spec/template/spec/containers/0/env/0/name', 'cmp': 'equals', 'value': 'RABBITMQ_DEFAULT_PASS'},
                    {'op': 'check', 'path': '/spec/template/spec/containers/0/env/1/name', 'cmp': 'equals', 'value': 'RABBITMQ_DEFAULT_USER'},
                    {'op': 'check', 'path': '/spec/template/spec/containers/0/env/2/name', 'cmp': 'equals','value': 'RABBITMQ_ERLANG_COOKIE'},
                    {'op': 'check', 'path': '/spec/template/spec/containers/0/ports/2/name', 'cmp': 'equals', 'value': 'prometheus'},

                    {'op': 'replace', 'path': '/metadata/name', 'value': self.object_name('statefulset')},
                    {'op': 'replace', 'path': '/metadata/namespace', 'value': self.namespace()},
                    {'op': 'merge', 'path': '/metadata', 'value': {'labels': {}}},
                    {'op': 'merge', 'path': '/metadata/labels', 'value': {'app': self.object_name('pod-label-app')}},
                    {'op': 'replace', 'path': '/spec/selector/matchLabels/app', 'value': self.object_name('pod-label-app')},
                    {'op': 'replace', 'path': '/spec/serviceName', 'value': self.object_name('service-headless')},
                    {'op': 'remove', 'path': '/spec/volumeClaimTemplates'},

                    {'op': 'replace', 'path': '/spec/template/metadata/name', 'value': self.object_name('pod-label-app')},
                    {'op': 'replace', 'path': '/spec/template/metadata/namespace', 'value': self.namespace()},
                    {'op': 'replace', 'path': '/spec/template/metadata/labels/app', 'value': self.object_name('pod-label-app')},
                    {'op': 'replace', 'path': '/spec/template/spec/serviceAccount',
                        'value': ValueData(value=self.object_name('service-account'),
                                           enabled=self.object_name('service-account') is not None)},
                    {'op': 'replace', 'path': '/spec/template/spec/volumes/2',
                     'value': KDataHelper_Volume.info(base_value={
                            'name': 'rabbitmq-data',
                    }, value=self.option_get('kubernetes.volumes.data'))},
                    {
                        'op': 'replace', 'path': '/spec/template/spec/containers/0/env/0',
                        'value': KDataHelper_Env.info(base_value={
                            'name': 'RABBITMQ_DEFAULT_PASS'
                        }, value=self.option_get('config.admin.password'), default_value={
                            'valueFrom': {
                                'secretKeyRef': {
                                    'name': self.object_name('config-secret'),
                                    'key': 'admin.password'
                                }
                            },
                        })
                    },
                    {
                        'op': 'replace', 'path': '/spec/template/spec/containers/0/env/1',
                        'value': KDataHelper_Env.info(base_value={
                            'name': 'RABBITMQ_DEFAULT_USER'
                        }, value=self.option_get('config.admin.username'), default_value={
                            'valueFrom': {
                                'secretKeyRef': {
                                    'name': self.object_name('config-secret'),
                                    'key': 'admin.username'
                                }
                            },
                        })
                    },
                    {
                        'op': 'replace', 'path': '/spec/template/spec/containers/0/env/2',
                        'value': KDataHelper_Env.info(base_value={
                            'name': 'RABBITMQ_ERLANG_COOKIE'
                        }, value=self.option_get('config.erlang_cookie'), default_value={
                            'valueFrom': {
                                'secretKeyRef': {
                                    'name': self.object_name('config-secret'),
                                    'key': 'erlang_cookie'
                                }
                            },
                        })
                    },
                    {
                        'op': 'add', 'path': '/spec/template/spec/containers/0/resources',
                        'value': ValueData(value=self.option_get('kubernetes.resources.statefulset'), disabled_if_none=True),
                    },
                ]

                if self.option_get('container.busybox') is not None:
                    ritempatch.append({'op': 'replace', 'path': '/spec/template/spec/initContainers/0/image', 'value': self.option_get('container.busybox')})
                if self.option_get('container.rabbitmq') is not None:
                    ritempatch.append({'op': 'replace', 'path': '/spec/template/spec/containers/0/image', 'value': self.option_get('container.rabbitmq')})
                if self.option_get('config.enable_prometheus') is False:
                    ritempatch.append({'op': 'remove', 'path': '/spec/template/spec/containers/0/ports/2'})
                if self.option_get('config.enable_prometheus') is not False and self.option_get('config.prometheus_annotation') is not False:
                    ritempatch.append({'op': 'merge', 'path': '/spec/template/metadata', 'value': {'annotations': {
                        'prometheus.io/scrape': QuotedStr('true'),
                        'prometheus.io/path': QuotedStr('/metrics'),
                        'prometheus.io/port': QuotedStr('15692'),
                    }}})
                if self.option_get('config.load_definitions') is not None:
                    ritempatch.append({
                        'op': 'add', 'path': '/spec/template/spec/volumes',
                        'value': KDataHelper_Volume.info(base_value={
                            'name': 'rabbitmq-config-load-definition',
                        }, value_if_kdata=self.option_get('config.load_definitions'), default_value={
                            'secret': {
                                'secretName': self.object_name('config-secret'),
                                'items': [{
                                    'key': 'load_definition.json',
                                    'path': 'load_definition.json',
                                }]
                            }
                        }, key_path='load_definition.json')
                    })
                    ritempatch.append({'op': 'add', 'path': '/spec/template/spec/containers/0/volumeMounts', 'value': {
                        'name': 'rabbitmq-config-load-definition',
                        'mountPath': '/etc/rabbitmq-load-definition',
                        'readOnly': True,
                    }})

                ritem = Object(jsonpatchext.apply_patch(ritem, ritempatch, in_place=False),
                               name=self.BUILDITEM_STATEFULSET, source=self.SOURCE_NAME, instance=self.basename())
            ret.append(ritem)

        for item in self._downloadedfiles['client-service.yaml']:
            ritem = item
            if ritem['kind'] == 'Service':
                ritempatch = [
                    {'op': 'check', 'path': '/metadata/name', 'cmp': 'equals', 'value': 'rabbitmq-client'},
                    {'op': 'check', 'path': '/metadata/namespace', 'cmp': 'equals', 'value': 'test-rabbitmq'},
                    {'op': 'check', 'path': '/spec/ports/1/name', 'cmp': 'equals', 'value': 'prometheus'},

                    {'op': 'replace', 'path': '/metadata/name', 'value': self.object_name('service')},
                    {'op': 'replace', 'path': '/metadata/namespace', 'value': self.namespace()},
                    {'op': 'replace', 'path': '/metadata/labels/app', 'value': self.object_name('pod-label-app')},
                    {'op': 'replace', 'path': '/spec/type', 'value': self.option_get('config.servicetype')},
                    {'op': 'replace', 'path': '/spec/selector/app', 'value': self.object_name('pod-label-app')},
                ]
                if self.option_get('config.enable_prometheus') is False:
                    ritempatch.append({'op': 'remove', 'path': '/spec/ports/1'})
                ritem = Object(jsonpatchext.apply_patch(ritem, ritempatch, in_place=False),
                               name=self.BUILDITEM_SERVICE, source=self.SOURCE_NAME, instance=self.basename())
            ret.append(ritem)

        self._check_object_must_have(ret, [self.BUILDITEM_SERVICE_HEADLESS, self.BUILDITEM_STATEFULSET,
                                           self.BUILDITEM_SERVICE], 'headless-service.yaml, statefulset.yaml, client-service.yaml')

        return ret
