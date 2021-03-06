"""Code generation utilities"""
import textwrap

from .utils import SchemaInfo, is_valid_identifier


class CodeSnippet(object):
    """Object whose repr() is a string of code"""
    def __init__(self, code):
        self.code = code

    def __repr__(self):
        return self.code


SCHEMA_CLASS_TEMPLATE = '''
class {classname}({basename}):
    """{docstring}"""
    _schema = {schema!r}
    _rootschema = {rootschema!r}

    {init_code}
'''


def schema_class(classname, schema, rootschema=None, basename='SchemaBase',
                 schemarepr=None, rootschemarepr=None):
    """Generate code for a schema class

    Parameters
    ----------
    classname : string
        The name of the class to generate
    schema : dict
        The dictionary defining the schema class
    rootschema : dict (optional)
        The root schema for the class
    basename : string (default: "SchemaBase")
        The name of the base class to use in the class definition
    schemarepr : CodeSnippet or object, optional
        An object whose repr will be used in the place of the explicit schema.
        This can be useful, for example, when the generated code should reference
        a predefined schema object. The user must ensure that the schema within
        the evaluated code is identical to the schema used to generate the code.
    rootschemarepr : CodeSnippet or object, optional
        An object whose repr will be used in the place of the explicit root
        schema.
    """
    rootschema = rootschema if rootschema is not None else schema
    schemarepr = schemarepr if schemarepr is not None else schema
    if rootschemarepr is None:
        if rootschema is schema:
            rootschemarepr = CodeSnippet('_schema')
        else:
            rootschemarepr = rootschema
    return SCHEMA_CLASS_TEMPLATE.format(
        classname=classname,
        basename=basename,
        schema=schemarepr,
        rootschema=rootschemarepr,
        docstring=docstring(classname=classname, schema=schema,
                            rootschema=rootschema, indent=4),
        init_code=init_code(classname=classname, schema=schema,
                            rootschema=rootschema, indent=4)
    )


def docstring(classname, schema, rootschema=None, indent=4):
    # TODO: add a general description at the top, derived from the schema.
    #       for example, a non-object definition should list valid type, enum
    #       values, etc.
    # TODO: use _get_args here for more information on allOf objects
    info = SchemaInfo(schema, rootschema)
    doc = ["{0} schema wrapper".format(classname)]
    if info.description:
        # TODO: wrap these description lines?
        wrapper = textwrap.TextWrapper(width=80,
                                       break_long_words=False,
                                       break_on_hyphens=False,
                                       drop_whitespace=False)
        doc = ['']
        for line in info.description.splitlines():
            doc.extend(wrapper.wrap(line))
    if info.properties:
        doc += ['',
                'Attributes',
                '----------']
        wrapper = textwrap.TextWrapper(width=80, initial_indent=4 * ' ',
                                       subsequent_indent=4 * ' ',
                                       break_long_words=False,
                                       break_on_hyphens=False)
        for prop, propinfo in info.properties.items():
            doc += ["{0} : {1}".format(prop, propinfo.short_description)]
            doc += wrapper.wrap(propinfo.description)
    if len(doc) > 1:
        doc += ['']
    return ("\n" + indent * " ").join(doc)


INIT_DEF = """
def __init__({arglist}):
    super({classname}, self).__init__({super_arglist})
""".lstrip()


# TODO: create func that gets list of args, required kwds, non-required kwds,
#       and optional kwds. Use this to recursively build-up keyword lists for
#       anyOf/allOf.


def _get_args(info):
    """Return the list of args & kwds for building the __init__ function"""
    # TODO: - set additional properties correctly
    #       - handle patternProperties etc.
    required = set()
    kwds = set()

    # TODO: specialize for anyOf/oneOf?

    if info.is_allOf():
        # recursively call function on all children
        arginfo = [_get_args(child) for child in info.allOf]
        nonkeyword = all(args[0] for args in arginfo)
        required = set.union(set(), *(args[1] for args in arginfo))
        kwds = set.union(set(), *(args[2] for args in arginfo))
        additional = all(args[3] for args in arginfo)
    elif info.is_empty() or info.is_compound():
        nonkeyword = True
        additional = True
    elif info.is_value():
        nonkeyword = True
        additional=False
    elif info.is_object():
        required = {p for p in info.required if is_valid_identifier(p)}
        kwds = {p for p in info.properties if is_valid_identifier(p)}
        kwds -= required
        nonkeyword = False
        additional = True
    else:
        raise ValueError("Schema object not understood")

    return (nonkeyword, required, kwds, additional)


def init_code(classname, schema, rootschema=None, indent=0, nodefault=()):
    """Return code suitablde for the __init__ function of a Schema class"""
    info = SchemaInfo(schema, rootschema=rootschema)
    nonkeyword, required, kwds, additional =_get_args(info)

    nodefault=set(nodefault)
    required -= nodefault
    kwds -= nodefault

    args = ['self']
    super_args = []

    if nodefault:
        args.extend(sorted(nodefault))
    elif nonkeyword:
        args.append('*args')
        super_args.append('*args')

    args.extend('{0}=Undefined'.format(p)
                for p in sorted(required) + sorted(kwds))
    super_args.extend('{0}={0}'.format(p)
                      for p in sorted(nodefault) + sorted(required) + sorted(kwds))

    if additional:
        args.append('**kwds')
        super_args.append('**kwds')

    arg_indent = ' ' * len('def __init__(')
    arg_wrapper = textwrap.TextWrapper(width=80,
                                       initial_indent=arg_indent,
                                       subsequent_indent=arg_indent,
                                       break_long_words=False)
    arglist = '\n'.join(arg_wrapper.wrap(', '.join(args))).lstrip()

    super_arg_indent = ' ' * len('    super({0}, self).__init__('.format(classname))
    super_arg_wrapper = textwrap.TextWrapper(width=80,
                                             initial_indent=super_arg_indent,
                                             subsequent_indent=super_arg_indent,
                                             break_long_words=False)
    super_arglist = '\n'.join(super_arg_wrapper.wrap(', '.join(super_args))).lstrip()

    code = INIT_DEF.format(classname=classname,
                           arglist=arglist,
                           super_arglist=super_arglist)
    if indent:
        code = code.replace('\n', '\n' + indent * ' ')
    return code
