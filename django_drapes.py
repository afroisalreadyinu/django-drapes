import inspect
import functools
import formencode
from decorator import decorator
import copy
import json


from django.template import Node, TemplateSyntaxError
from django import template
from django.http import HttpResponse
try:
    from django.shortcuts import render
except ImportError:
    pass


class PermissionException(Exception):
    pass

class MultipleValidationErrors(Exception):

    def __init__(self, errors, *args, **kwargs):
        self.errors = errors

class DomainError(Exception):
    pass


class ModelValidator(formencode.FancyValidator):

    messages = dict(
        no_instance = "No instance could be found.",
        multiple_instances = "Multiple entries for validator."
        )

    def __init__(self, model, get_by='id', *args, **kwargs):
        super(ModelValidator, self).__init__(*args, **kwargs)
        self.model = model
        self.get_by = get_by


    def _to_python(self, value, state):
        #TODO if it's an id field or something integery make it an
        #integer
        kwargs = {self.get_by:value}
        rows = self.model.objects.filter(**kwargs)
        if len(rows) == 0:
            raise formencode.Invalid(self.message('no_instance', state),
                                     value, state)
        if len(rows) != 1:
            raise formencode.Invalid(self.message('multiple_instances', state),
                                     value, state)
        return rows[0]


def _build_args_dict(function, *args, **kwargs):
    argspec = inspect.getargspec(function)
    args_dict = dict(zip(argspec[0], args))
    args_dict.update(kwargs)
    return args_dict

def _is_view_func(function):
    argspec = inspect.getargspec(function)
    return argspec.args and argspec.args[0] == 'request'


def _perm_to_bool(obj, user, permission):
    if callable(permission):
        return bool(permission(obj))
    if hasattr(obj, permission):
        attr = getattr(obj, permission)
        if callable(attr):
            return bool(attr())
        return bool(attr)
    if PERMISSION_REGISTER.has_key(obj.__class__):
        try:
            perm = getattr(PERMISSION_REGISTER[obj.__class__](obj),
                           permission)
        except AttributeError:
            pass
        else:
            if callable(perm):
                return perm(user)
            else:
                return bool(perm)
    raise ValueError("Permission %r is not applicable to object %r" %
                     (permission, obj))

def _call_wrapped_func(args_dict, func):
    argspec = inspect.getargspec(func)
    args = [args_dict[arg] for arg in argspec.args]
    kwargs = dict((key, value) for key, value in args_dict.iteritems()
                  if key not in argspec.args)
    return func(*args, **kwargs)

def is_json(request):
    request_dict = (request.POST if request.method == 'POST'
                    else request.GET)
    return request_dict.has_key('json') and request_dict['json']


def require(**permissions):
    """
    A decorator for checking permissions on in incoming
    request. Accepts keyword arguments referring either to user
    (accessed through request.user) or the positional or keyword
    arguments of a view function, and a string corresponding to the
    permission. The user is assumed to be an attribute of the first
    argument of the controller. What permission to execute is
    determined in the following order:
    - An attribute of the object
    - A method of the object
    - A method of the model permission (a subclass of ModelPermission;
      see below) that accepts a user as argument.
    """
    @decorator
    def deco(view_func, *args, **kwargs):
        args_dict = _build_args_dict(view_func, *args, **kwargs)
        args_dict['user'] = args[0].user
        for key, permission in permissions.iteritems():
            if not _perm_to_bool(args_dict[key], args[0].user, permission):
                raise PermissionException('%s is not allowed to %s' %
                                          (key, permission))
        return view_func(*args, **kwargs)

    return deco

def verify(**conversions):
    """
    A decorator that turns values passed to the controller into a more
    usable form (such as models), and throws suitable exceptions when
    that does not work. The conversions should be a dictionary-like
    object, matching controller arguments to a validator. The values
    for the conversions are searched in the arguments for the
    controller function and the get parameters (if the request is a
    get, of course). This causes a mismatch between the url definition
    and the function signature, since one can't specify get parameters
    in a url entry, and a controller normally has to look up a get
    parameter in the get dict. Because of this mismatch, the
    controller has to include a keyword argument that defaults to an
    unused value in order to force its conversion from the get
    parameter into an argument. If you want the GET dictionary to be
    included in verification, the first argument of the controller has
    to be called 'request'.
    """

    def _validate(argname, argval):
        if conversions.has_key(argname):
            validator = conversions[argname]
            return validator.to_python(argval)
        return argval

    @decorator
    def deco(view_func, *args, **kwargs):
        args_dict = _build_args_dict(view_func, *args, **kwargs)

        if _is_view_func(view_func):
            request = args[0]
            if request.method == "GET":
                args_dict.update(dict(request.GET))

        validated_args_dict = dict()
        errors = []
        for argument_name, value in args_dict.iteritems():
            try:
                validated_args_dict[argument_name] = _validate(argument_name,
                                                                    value)
            except formencode.Invalid, f:
                errors.append(f)
        if len(errors) == 1:
            raise errors[0]
        elif errors:
            raise MultipleValidationErrors(errors)

        return _call_wrapped_func(validated_args_dict, view_func)
    return deco

class NonmatchingHandlerArgspecs(Exception):
    pass

class verify_post(object):
    """
    A decorator for splitting responsibilities and improving
    validations on a page that handles both get and post requests.
    """

    def __init__(self,
                 form_class,
                 valid_handler,
                 pass_user=None):
        self.form_class = form_class
        self.valid_handler = valid_handler
        self.pass_user = pass_user

    def _match_handlers(self, default_handler, valid_handler):
        default_args = copy.copy(inspect.getargspec(default_handler).args)
        default_args.remove('invalid_form')
        valid_args = copy.copy(inspect.getargspec(valid_handler).args)
        valid_args.remove('form')
        if not default_args == valid_args:
            raise NonmatchingHandlerArgspecs()


    def __call__(self, view_func):
        self._match_handlers(view_func, self.valid_handler)
        def replacement_func(request, *args, **kwargs):
            if not request.method == 'POST':
                return view_func(request, *args, **kwargs)
            if self.pass_user:
                form = self.form_class(request.POST, user=request.user)
            else:
                form = self.form_class(request.POST)
            if not form.is_valid():
                kwargs['invalid_form'] = form
                return view_func(request, *args, **kwargs)
            else:
                kwargs['form'] = form
                return self.valid_handler(request,
                                          *args,
                                          **kwargs)
        return replacement_func


def render_with(template_name):
    """
    A decorator that turns the output of a controller into a rendered
    template.
    """
    @decorator
    def replacement_func(view_func, *args, **kwargs):
        response_dict = view_func(*args, **kwargs)
        if not isinstance(response_dict, dict):
            return response_dict
        real_template_name = template_name
        if response_dict.has_key('template'):
            real_template_name = response_dict['template']
        if real_template_name == 'json' or is_json(args[0]):
            return HttpResponse(json.dumps(response_dict),
                                'application/javascript')
        return render(args[0],
                      real_template_name,
                      response_dict)
    return replacement_func


def json_or_redirect(redirect):
    @decorator
    def replacement_func(view_func, *args, **kwargs):
        response_dict = view_func(*args, **kwargs)
        if is_json(args[0]):
            return HttpResponse(json.dumps(response_dict),
                                'application/javascript')
        return HttpResponseRedirect(redirect)
    return replacement_func


class ModelAttributeMixin(object):

    def __getattr__(self, attr_name):
        if hasattr(self.obj, attr_name):
            return getattr(self.obj, attr_name)
        raise AttributeError("Neither %s nor %s view have attribute %s" %
                             (self.obj.__class__,
                              self.__class__,
                              attr_name))


VIEW_REGISTER = {}

class ModelViewMeta(type):

    def __init__(cls, name, bases, dct):
        super(ModelViewMeta, cls).__init__(name, bases, dct)
        if 'model' in dct and dct['model']:
            VIEW_REGISTER[dct['model']] = cls


class ModelView(ModelAttributeMixin):

    __metaclass__ = ModelViewMeta
    model = None

    def __init__(self, obj):
        self.obj = obj


PERMISSION_REGISTER = {}

class ModelPermissionMeta(type):

    def __init__(cls, name, bases, dct):
        super(ModelPermissionMeta, cls).__init__(name, bases, dct)
        if 'model' in dct and dct['model']:
            PERMISSION_REGISTER[dct['model']] = cls


class ModelPermission(ModelAttributeMixin):

    __metaclass__ = ModelPermissionMeta
    model = None

    def __init__(self, obj):
        self.obj = obj


class ModelViewNode(Node):
    def __init__(self, model, viewname):
        self.model = template.Variable(model)
        self.viewname = viewname

    def render(self, context):
        model = self.model.resolve(context)
        view_class = VIEW_REGISTER[model.__class__]
        view = view_class(model)
        view_thing = getattr(view, self.viewname)
        if callable(view_thing):
            return view_thing()
        return view_thing

def modelview(parser, token):
    """
    Usage:
    {% modelview model_instance view_name %}
    """
    bits = token.split_contents()
    if len(bits) != 3:
        raise TemplateSyntaxError, "'%s' tag requires two arguments" % bits[0]
    return ModelViewNode(bits[1],bits[2])


class ModelPermissionNode(Node):
    """
    Usage: {% if_allowed user model_instance permission_name %}
           blah blah blah
           {% else %}
           yada yada yada
           {% end_if_allowed %}
     The else part is optional
    """
    def __init__(self,
                 user,
                 permission_name,
                 model_instance,
                 nodelist_true,
                 nodelist_false):
        self.user = template.Variable(user)
        self.permission_name = permission_name
        self.model_instance = template.Variable(model_instance)
        self.nodelist_true = nodelist_true
        self.nodelist_false = nodelist_false

    def render(self, context):
        user = self.user.resolve(context)
        model_instance = self.model_instance.resolve(context)
        permissions = PERMISSION_REGISTER[model_instance.__class__](model_instance)
        if getattr(permissions, self.permission_name)(user):
            return self.nodelist_true.render(context)
        return self.nodelist_false.render(context)


def model_permission(parser, token):
    bits = token.split_contents()
    if len(bits) != 4:
        raise TemplateSyntaxError, "'%s' tag requires three arguments" % bits[0]

    end_tag = 'end_' + bits[0]
    nodelist_true = parser.parse(('else', end_tag))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse((end_tag,))
        parser.delete_first_token()
    else:
        nodelist_false = template.NodeList()

    return ModelPermissionNode(bits[1],bits[2],bits[3],
                               nodelist_true, nodelist_false)
