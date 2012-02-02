=============
django-drapes
=============

django-drapes is a small library that aims to ease authorization and
user input verification. Most of the functionality is packed into
decorators intended for applying to views, hence the name
django-drapes.

Decorators
==========

verify
------

verify is a decorator that turns values passed to the controller into
a more usable form (such as models), and throws suitable exceptions
when this does not work. The conversions are specified as keyword
arguments with a validator matching the name of the controller
argument. The validators have to implement the `formencode validator
interface
<http://www.formencode.org/en/latest/Validator.html>`_.

Here is a simple example::

    from django_drapes import verify
    import formencode

    @verify(int_arg=formencode.validators.Int())
    def controller(request, int_arg):
    	return 'Argument is %d' % int_arg

The controller receives int_arg as an integer, and you do not need to
do the conversions in the controller.

The values for the conversions are searched in the arguments for the
controller function, and additionally the get parameters if the
request is a get. This causes a mismatch between the url definition
and the function signature, since one can't specify get parameters in
a url entry, and a controller normally has to look up a get parameter
in request.GET. Because of this mismatch, in case you want to verify a
GET parameter, the controller has to include this parameter as a
keyword argument in order to force conversion.

The most frequently done conversion is selecting a model with a unique
field. django-drapes has a built in validator for this kind of
conversion, called ModelValidator. It can be used as follows::

    from django.db import models
    from django_drapes import verify, ModelValidator
    import formencode

    class Project(models.Model):
        slug = models.SlugField(unique=True)

    @verify(item=ModelValidator(get_by=slug))
    def controller(request, item):
    	return "Item's slug is %s" % item.slug


require
-------

require checks permissions on an incoming request to a controller.
Just like validate, it accepts keyword arguments with key referring
either to user (accessed through request.user) or the positional or
keyword arguments of a view function.  Value must be a string
corresponding to the permission. What the permission refers to is
determined in the following order:

- An attribute of the object
- A method of the object that does not require any arguments
- A method of the model permission (a subclass of ModelPermission;
  see below) that accepts a user as argument.

Here is a very simple example::

    from django.db import models
    from django_drapes import verify, ModelValidator
    import formencode

    class Project(models.Model):
        slug = models.SlugField(unique=True)
	published = models.BooleanField(default=False)

    @verify(item=ModelValidator(get_by=slug))
    @require(item='published')
    def controller(request, item):
    	return "Item's slug is %s" % item.slug

Permissions can be added to models using the ModelPermission
class, as follows::

    from django.db import models
    from django_drapes import verify, ModelValidator
    import formencode

    class Project(models.Model):
        slug = models.SlugField()

    @verify(item=ModelValidator(get_by=slug))
    @require(item='can_view')
    def controller(request, item):
    	return "Na"

    class ProjectPermissions(ModelPermission):
        model = Project
	def can_view(self, user):
            return user.username == 'horst'

The only person who can view this item is the one named horst.


verify_post
-----------

verify_post is a decorator for splitting the handling of user input
through forms into two parts.

render_with
-----------
render_with turns dictionary return values into rendered templates.


Template tags
=============

if_allowed and modelview
