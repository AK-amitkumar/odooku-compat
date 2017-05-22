import json


class DataConfig(object):

    def __init__(self, excludes=None, includes=None, models=None):
        self.excludes = excludes or []
        self.includes = includes or []
        self.models = {
            k: ModelConfig(**v) for
            (k, v) in (models or {}).iteritems()
        }

    @classmethod
    def from_file(cls, path):
        with open(path, 'r') as fp:
            return cls(**json.load(fp))

    @classmethod
    def defaults(cls):
        return cls(excludes=[
            'res.*',
            'ir.*',
            'base.*',
            'base_import.tests.*'
        ])


class ModelConfig(object):

    def __init__(self, excludes=None, includes=None, fields=None, nk=None):
        self.excludes = excludes or []
        self.includes = includes or []
        self.fields = fields or {}
        self.nk = nk or []
