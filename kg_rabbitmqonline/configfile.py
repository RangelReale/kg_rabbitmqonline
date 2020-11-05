from typing import Any, Optional, Mapping

from kubragen.builder import Builder
from kubragen.configfile import ConfigFile, ConfigFileOutput, ConfigFileOutput_DictSingleLevel
from kubragen.exception import InvalidParamError
from kubragen.option import OptionDef
from kubragen.options import OptionGetter, Options, option_root_get


class RabbitMQOnlineConfigFileOptions(Options):
    """
    Options for RabbitMQ config file.

    .. list-table::
        :header-rows: 1

        * - option
          - description
          - allowed types
          - default value
        * - enable.log_level
          - set log level on config file
          - bool
          - ```True```
        * - enable.cluster_formation
          - set cluster formation on config file
          - bool
          - ```True```
        * - config.extra_config
          - extra config to add fo config file
          - Mapping
          - ```{}```
    """
    def define_options(self) -> Optional[Any]:
        """
        Declare the options for the RabbitMQ config file.

        :return: The supported options
        """
        return {
            'enable': {
                'log_level': OptionDef(required=True, default_value=True, allowed_types=[bool]),
                'cluster_formation': OptionDef(required=True, default_value=True, allowed_types=[bool]),
            },
            'config': {
                'extra_config': OptionDef(default_value={}, allowed_types=[Mapping]),
            },
        }


class RabbitMQOnlineConfigFile(ConfigFile):
    """
    RabbitMQ main configuration file in SysCtl format (3.7.0 or higher).
    """
    options: RabbitMQOnlineConfigFileOptions

    def __init__(self, options: Optional[RabbitMQOnlineConfigFileOptions] = None):
        if options is None:
            options = RabbitMQOnlineConfigFileOptions()
        self.options = options

    def option_get(self, name: str):
        return option_root_get(self.options, name)

    def get_value(self, options: OptionGetter) -> ConfigFileOutput:
        if not isinstance(options, Builder):
            raise InvalidParamError('Options must be a "Builder" instance')

        ret = {}
        if self.option_get('enable.log_level'):
            ret.update({
                'log.console.level': options.option_get('config.loglevel'),
            })
        if self.option_get('enable.cluster_formation'):
            ret.update({
                'cluster_formation.peer_discovery_backend': 'k8s',
                'cluster_formation.k8s.host': 'kubernetes.default.svc.cluster.local',
                'cluster_formation.k8s.address_type': 'hostname',
                'cluster_formation.k8s.service_name': options.object_name('service-headless'),
                'queue_master_locator': 'min-masters',
            })

        load_definitions = options.option_get('config.load_definitions')
        if load_definitions is not None:
            ret.update({
                'load_definitions': '/etc/rabbitmq-load-definition/load_definition.json',
            })

        extra_config = self.option_get('config.extra_config')
        if extra_config is not None:
            ret.update(extra_config)

        return ConfigFileOutput_DictSingleLevel(ret)
