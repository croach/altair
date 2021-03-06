import six

import pandas as pd

from .schema import *
from .schema import core, channels, Undefined

from .data import data_transformers, pipe
from ...utils import infer_vegalite_type, parse_shorthand_plus_data, use_signature
from .display import renderers


SCHEMA_URL = "https://vega.github.io/schema/vega-lite/v2.json"


def _get_channels_mapping():
    mapping = {}
    for attr in dir(channels):
        cls = getattr(channels, attr)
        if isinstance(cls, type) and issubclass(cls, SchemaBase):
            mapping[cls] = attr.replace('Value', '').lower()
    return mapping


class TopLevelMixin(object):
    def _prepare_data(self):
        if isinstance(self.data, (dict, core.Data, core.InlineData,
                                  core.UrlData, core.NamedData)):
            pass
        elif isinstance(self.data, pd.DataFrame):
            self.data = pipe(self.data, data_transformers.get())
        elif isinstance(self.data, six.string_types):
            self.data = core.UrlData(self.data)

    def to_dict(self, *args, **kwargs):
        # TODO: it's a bit weird that to_dict modifies the object.
        #       Should we create a copy first?
        original_data = getattr(self, 'data', Undefined)
        self._prepare_data()

        # We make use of two context markers:
        # - 'data' points to the data that should be referenced for column type
        #   inference.
        # - 'toplevel' is a boolean flag that is assumed to be true; if it's
        #   true then a "$schema" arg is added to the dict.
        context = kwargs.get('context', {}).copy()
        if original_data is not Undefined:
            context['data'] = original_data
        if context.get('top_level', True):
            # since this is top-level we add $schema if it's missing
            if '$schema' not in self._kwds:
                self._kwds['$schema'] = SCHEMA_URL
            # subschemas below this one are not top-level
            context['top_level'] = False
        kwargs['context'] = context
        return super(TopLevelMixin, self).to_dict(*args, **kwargs)

    # Layering and stacking

    def __add__(self, other):
        return LayerChart([self, other])

    def __and__(self, other):
        return VConcatChart([self, other])

    def __or__(self, other):
        return HConcatChart([self, other])

    # Display-related methods

    def _repr_mimebundle_(self, include, exclude):
        """Return a MIME bundle for display in Jupyter frontends."""
        return renderers.get()(self.to_dict())


class Chart(TopLevelMixin, core.TopLevelFacetedUnitSpec):
    def __init__(self, data=Undefined, encoding=Undefined, mark=Undefined,
                 width=400, height=300, **kwargs):
        super(Chart, self).__init__(data=data, encoding=encoding, mark=mark,
                                    width=width, height=height, **kwargs)

    @use_signature(core.MarkDef)
    def mark_area(self, **kwargs):
        copy = self.copy(deep=True, ignore=['data'])
        if kwargs:
            copy.mark = core.MarkDef(type='area', **kwargs)
        else:
            copy.mark = 'area'
        return copy

    @use_signature(core.MarkDef)
    def mark_bar(self, **kwargs):
        copy = self.copy(deep=True, ignore=['data'])
        if kwargs:
            copy.mark = core.MarkDef(type='bar', **kwargs)
        else:
            copy.mark = 'bar'
        return copy

    @use_signature(core.MarkDef)
    def mark_line(self, **kwargs):
        copy = self.copy(deep=True, ignore=['data'])
        if kwargs:
            copy.mark = core.MarkDef(type='line', **kwargs)
        else:
            copy.mark = 'line'
        return copy

    @use_signature(core.MarkDef)
    def mark_point(self, **kwargs):
        copy = self.copy(deep=True, ignore=['data'])
        if kwargs:
            copy.mark = core.MarkDef(type='point', **kwargs)
        else:
            copy.mark = 'point'
        return copy

    @use_signature(core.MarkDef)
    def mark_text(self, **kwargs):
        copy = self.copy(deep=True, ignore=['data'])
        if kwargs:
            copy.mark = core.MarkDef(type='text', **kwargs)
        else:
            copy.mark = 'text'
        return copy

    @use_signature(core.MarkDef)
    def mark_tick(self, **kwargs):
        copy = self.copy(deep=True, ignore=['data'])
        if kwargs:
            copy.mark = core.MarkDef(type='tick', **kwargs)
        else:
            copy.mark = 'tick'
        return copy

    @use_signature(core.MarkDef)
    def mark_rect(self, **kwargs):
        copy = self.copy(deep=True, ignore=['data'])
        if kwargs:
            copy.mark = core.MarkDef(type='rect', **kwargs)
        else:
            copy.mark = 'rect'
        return copy

    @use_signature(core.MarkDef)
    def mark_rule(self, **kwargs):
        copy = self.copy(deep=True, ignore=['data'])
        if kwargs:
            copy.mark = core.MarkDef(type='rule', **kwargs)
        else:
            copy.mark = 'rule'
        return copy

    @use_signature(core.MarkDef)
    def mark_circle(self, **kwargs):
        copy = self.copy(deep=True, ignore=['data'])
        if kwargs:
            copy.mark = core.MarkDef(type='circle', **kwargs)
        else:
            copy.mark = 'circle'
        return copy

    @use_signature(core.MarkDef)
    def mark_square(self, **kwargs):
        copy = self.copy(deep=True, ignore=['data'])
        if kwargs:
            copy.mark = core.MarkDef(type='square', **kwargs)
        else:
            copy.mark = 'square'
        return copy

    @use_signature(core.MarkDef)
    def mark_geoshape(self, **kwargs):
        copy = self.copy(deep=True, ignore=['data'])
        if kwargs:
            copy.mark = core.MarkDef(type='geoshape', **kwargs)
        else:
            copy.mark = 'geoshape'
        return copy

    # TODO: add configure_* methods

    def encode(self, *args, **kwargs):
        # First convert args to kwargs by inferring the class from the argument
        if args:
            mapping = _get_channels_mapping()
            for arg in args:
                encoding = mapping.get(type(arg), None)
                if encoding is None:
                    raise NotImplementedError("non-keyword arg of type {0}"
                                              "".format(type(arg)))
                if encoding in kwargs:
                    raise ValueError("encode: encoding {0} specified twice"
                                     "".format(encoding))
                kwargs[encoding] = arg

        for prop, field in list(kwargs.items()):
            if not isinstance(field, SchemaBase):
                cls = getattr(channels, prop.title())
                # Don't validate now, because field will be computed
                # as part of the to_dict() call.
                kwargs[prop] = cls.from_dict(field, validate=False)
        copy = self.copy(deep=True, ignore=['data'])

        # get a copy of the dict representation of the previous encoding
        encoding = copy.encoding
        if encoding is Undefined:
            encoding = {}
        elif isinstance(encoding, dict):
            pass
        else:
            encoding = {k: v for k, v in encoding._kwds.items()
                        if v is not Undefined}

        # update with the new encodings, and apply them to the copy
        encoding.update(kwargs)
        copy.encoding = core.EncodingWithFacet(**encoding)
        return copy

    def interactive(self, name='grid', bind_x=True, bind_y=True):
        """Make chart axes scales interactive

        Parameters
        ----------
        name : string
            The selection name to use for the axes scales. This name should be
            unique among all selections within the chart.
        """
        encodings = []
        if bind_x:
            encodings.append('x')
        if bind_y:
            encodings.append('y')
        copy = self.copy(deep=True, ignore=['data'])
        # TODO: don't overwrite previous selections?
        copy.selection = {name: {'bind': 'scales',
                                 'type': 'interval',
                                 'encodings': encodings}}
        return copy

    def properties(self, **kwargs):
        copy = self.copy(deep=True, ignore=['data'])
        for key, val in kwargs.items():
            setattr(copy, key, val)
        return copy


class HConcatChart(TopLevelMixin, core.TopLevelHConcatSpec):
    def __init__(self, hconcat, **kwargs):
        # TODO: move common data to top level?
        # TODO: check for conflicting interaction
        super(HConcatChart, self).__init__(hconcat=list(hconcat), **kwargs)

    # TODO: think about the most useful class API here


def hconcat(*charts, **kwargs):
    """Concatenate charts horizontally"""
    return HConcatChart(charts, **kwargs)


class VConcatChart(TopLevelMixin, core.TopLevelVConcatSpec):
    def __init__(self, vconcat, **kwargs):
        # TODO: move common data to top level?
        # TODO: check for conflicting interaction
        super(VConcatChart, self).__init__(vconcat=list(vconcat), **kwargs)

    # TODO: think about the most useful class API here


def vconcat(*charts, **kwargs):
    """Concatenate charts vertically"""
    return VConcatChart(charts, **kwargs)


class LayerChart(TopLevelMixin, core.TopLevelLayerSpec):
    def __init__(self, layer, **kwargs):
        # TODO: move common data to top level?
        # TODO: check for conflicting interaction
        super(LayerChart, self).__init__(layer=list(layer), **kwargs)

    # TODO: think about the most useful class API here


def layer(*charts, **kwargs):
    """layer multiple charts"""
    return LayerChart(charts, **kwargs)
