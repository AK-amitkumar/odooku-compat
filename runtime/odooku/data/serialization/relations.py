from odooku.data.serialization.base import BaseFieldSerializer
from odooku.data.match import match_any
from odooku.data.exceptions import ModelMissing

import logging


_logger = logging.getLogger(__name__)


class RelationSerializer(BaseFieldSerializer):

    def __init__(self, field_name, relation, required=False):
        super(RelationSerializer, self).__init__(field_name, required=required)
        self.relation = relation

    @classmethod
    def parse(cls, field_name, field, config, model_name, **kwargs):
        relation = field['relation']
        required = field['required']
        model_config = config.models.get(relation)
        if model_config and model_config.nk or not(
                    config.includes and not match_any(relation, config.includes)
                    or match_any(relation, config.excludes)
                ):
            return cls(field_name, relation, required=required)


class ManyToOneSerializer(RelationSerializer):

    def serialize(self, record, context):
        value = record.read([self.field_name])[0][self.field_name]
        if value:
            serializer = context.serializers[self.relation]
            context.add_dependency(self.relation, value[0], self)
            return serializer.serialize_id(value[0], context)
        return False

    def deserialize(self, values, context):
        value = values[self.field_name]
        if value:
            serializer = context.serializers[self.relation]
            return serializer.deserialize_id(value, context)
        return False


class ManyToManySerializer(RelationSerializer):

    def serialize(self, record, context):
        if context.delayed:
            result = []
            value = record.read([self.field_name])[0][self.field_name]
            if value:
                serializer = context.serializers[self.relation]
                for id in value:
                    context.add_dependency(self.relation, id, self)
                    result.append(serializer.serialize_id(id, context))
            return result
        else:
            context.delay_field(self.field_name)

    def deserialize(self, values, context):
        result = []
        value = values[self.field_name]
        if value:
            serializer = context.serializers[self.relation]
            for id in value:
                result.append(serializer.deserialize_id(id, context))
        return [(6, 0, result)]


class GenericRelationSerializer(BaseFieldSerializer):

    def __init__(self, field_name, model_field, required=False):
        super(GenericRelationSerializer, self).__init__(field_name, required=required)
        self.model_field = model_field

    @classmethod
    def parse(cls, field_name, field, model_name, field_config, **kwargs):
        model_field = field_config.get('model_field')
        if not model_field:
            raise Exception("Generic field requires a model_field")

        required = field['required']
        return cls(field_name, model_field, required=required)


class GenericManyToOneSerializer(GenericRelationSerializer):

    def serialize(self, record, context):
        if context.delayed:
            value = record.read([self.field_name])[0][self.field_name]
            model_name = record.read([self.model_field])[0][self.model_field]
            if value and model_name and model_name in context.serializers:
                serializer = context.serializers[model_name]
                try:
                    return [
                        model_name,
                        serializer.serialize_id(value, context)
                    ]
                except ModelMissing:
                    _logger.info("Skipping generic relation %s -> %s:%s", self.field_name, model_name, value)

            return False
        else:
            context.delay_field(self.field_name)

    def deserialize(self, values, context):
        value = values[self.field_name]
        if value:
            if value[0] in context.serializers:
                serializer = context.serializers[value[0]]
                return serializer.deserialize_id(value[1], context)
        return False
