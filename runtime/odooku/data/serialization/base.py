class BaseFieldSerializer(object):

    def __init__(self, field_name, required=False):
        self.field_name = field_name
        self.required = required

    def serialize(self, record, context):
        raise NotImplementedError()

    def deserialize(self, record, context):
        raise NotImplementedError()

    @classmethod
    def parse(cls, field_name, field, **kwargs):
        return cls(field_name, field['required'])

    def __repr__(self):
        return self.field_name
