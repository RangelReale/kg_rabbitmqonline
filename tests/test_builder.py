import unittest

from kubragen import KubraGen
from kubragen.jsonpatch import FilterJSONPatches_Apply, ObjectFilter, FilterJSONPatch
from kubragen.provider import Provider_Generic

from kg_rabbitmqonline import RabbitMQOnlineBuilder, RabbitMQOnlineOptions


class TestBuilder(unittest.TestCase):
    def setUp(self):
        self.kg = KubraGen(provider=Provider_Generic())

    def test_empty(self):
        rabbit_config = RabbitMQOnlineBuilder(kubragen=self.kg)
        self.assertEqual(rabbit_config.object_name('config'), 'rabbitmq-config')
        self.assertEqual(rabbit_config.object_name('statefulset'), 'rabbitmq')

    def test_basedata(self):
        rabbit_config = RabbitMQOnlineBuilder(kubragen=self.kg, options=RabbitMQOnlineOptions({
            'namespace': 'myns',
            'basename': 'myrabbit',
            'config': {
                'admin': {
                    'username': 'rabbit@example.com',
                    'password': 'my-rabbit-password',
                }
            },
            'kubernetes': {
                'volumes': {
                    'data': {
                        'emptyDir': {},
                    }
                }
            }
        }))
        self.assertEqual(rabbit_config.object_name('config'), 'myrabbit-config')
        self.assertEqual(rabbit_config.object_name('statefulset'), 'myrabbit')

        FilterJSONPatches_Apply(items=rabbit_config.build(rabbit_config.BUILD_SERVICE), jsonpatches=[
            FilterJSONPatch(filters=ObjectFilter(names=[rabbit_config.BUILDITEM_SERVICE]), patches=[
                {'op': 'check', 'path': '/metadata/name', 'cmp': 'equals', 'value': 'myrabbit'},
                {'op': 'check', 'path': '/metadata/namespace', 'cmp': 'equals', 'value': 'myns'},
            ]),
        ])
