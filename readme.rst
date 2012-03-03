=============
django-drapes
=============

django-drapes is a small library that aims to ease authorization and
user input verification. Most of the functionality is packed into
decorators intended for applying to views, hence the name
django-drapes. The decorators:

- verify_: Validate and convert values passed to a controller
- require_: Check for permissions
- verify_post_: Validate and process POST requests
- render_with_: Render a dictionary with a template or json

There are also two template tags which can be used in combination with
these decorators:

- if_allowed_: Display content depending on user permissions
- modelview_: Output a model view

Decorators
==========

.. _verify:

verify
------

``verify`` is a decorator that turns values passed to the controller
into a more usable form (such as models), and throws suitable
exceptions when this does not work. The conversions are specified as
keyword arguments with a validator matching the name of the controller
argument. The validators have to implement the `formencode validator
interface <http://www.formencode.org/en/latest/Validator.html>`_.

Here is a simple example::

    from django_drapes import verify
    import formencode

    @verify(int_arg=formencode.validators.Int())
    def controller(request, int_arg):
    	return 'Argument is %d' % int_arg

The controller receives ``int_arg`` as an integer, obviating the need
to convert in the controller.

The values for the conversions are searched in the arguments for the
controller function, and additionally the GET parameters if the
request is a GET. This causes a mismatch between the url definition
and the function signature, since one can't specify get parameters in
a url entry, and a controller normally has to look up a GET parameter
in request.GET. Because of this mismatch, in case you want to verify a
GET parameter, you should include this parameter as a keyword argument
in the controller signature.

The most frequently done conversion is selecting a model with a unique
field. django-drapes has a built in validator for this kind of
conversion, called ``ModelValidator``. It can be used as follows::

    from django.db import models
    from django_drapes import verify, ModelValidator

    class Project(models.Model):
        slug = models.SlugField(unique=True)

    @verify(item=ModelValidator(get_by='slug'))
    def controller(request, item):
    	return "Item's slug is %s" % item.slug

An advanced feature implemented by ``ModelValidator`` is looking up a
model by multiple keys. In order to do this, you should initialize
``ModelValidator`` with a list of strings as ``get_by``. These strings
should be in the form ``model_field=view_arg``, matching arguments to
a view to fields on a model. For example, let's assume that we have a
project where users can create items identified by slugs. Items
belonging to different users can have the same slug, and the page for
such an item is identified by the name of the user and the slug of the
item. In that case, drapes decorators can be used as follows::

    @verify(owner=ModelValidator(User, get_by='username'))
    @verify(item=ModelValidator(Project, get_by=['slug=item','owner=owner']))
    @render_with('view_item.html')
    def view_item(request, owner, item):
	return dict(item=item)

This case also demonstrates `Mixing the decorators`_.

.. _require:

require
-------

``require`` checks permissions on an incoming request to a controller.
Just like validate, it accepts keyword arguments with key referring
either to user (accessed through ``request.user``) or the positional
or keyword arguments of a view function.  Value must be a string
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

    class Thing(models.Model):
        slug = models.SlugField(unique=True)
	published = models.BooleanField(default=False)

    @verify(item=ModelValidator(Thing, get_by=slug))
    @require(user='is_authenticated',
             thing='published')
    def controller(request, thing):
    	return "This thing's slug is %s" % item.slug

Permissions can be added to models by subclassing the ModelPermission
class, and setting a model as the class attribute::

    from django.db import models
    from django.shortcuts import render
    from django_drapes import (verify,
                               ModelValidator,
			       ModelPermission)

    class Thing(models.Model):
        slug = models.SlugField()

    class ThingPermissions(ModelPermission):
        model = Thing
	def can_view(self, user):
            return user.username == 'horst'

    @verify(thing=ModelValidator(get_by=slug))
    @require(thing='can_view')
    def controller(request, thing):
    	return render(request, 'thing.htm', dict(thing=thing))

The only person who can view this item is the one named horst. The
default selector used by ``ModelValidator`` is model id; this can be
overriden using the ``get_by`` argument, as seen above.

.. _verify_post:

verify_post
-----------

``verify_post`` is a decorator for easing the workflow with form
input. The aim is to split the handling of user input through forms
into the presentation of empty or erronuous forms, and the processing
of a valid form.

There are two ways to use verify_post. The first is the simple case,
where the same entry point to an app should display a form for GET,
and also process it when it gets POSTed. In this case,
``verify_post.single`` should be used. This factory method accepts two
positional arguments: the form used to verify the POST, and the
handler to call if the form validates::

    from django import forms
    from django_drapes import verify_post
    from django.http import HttpResponseRedirect
    from django.shortcuts import render_to_response
    #we are assuming the models exist somewhere
    from .models import Thing
    from django_drapes import (verify,
                               verify_post,
                               ModelValidator)

    class ThingForm(forms.Form):
        name = forms.CharField(required=True, min_length=4)

    def create_thing(request, item, form):
        thing = Thing(name=form.data['name'])
        thing.save()
	return HttpResponseRedirect(thing.get_absolute_url())

    @verify(item=ModelValidator())
    @verify_post.single(ThingForm, create_thing)
    @require(item='can_view')
    def controller(request, item, invalid_form=None):
    	return render_to_response('form_template.html',
	                          dict(form=ThingForm()))

Some notes on this example. When you are handling single forms, the
controller must have a keyword argument ``invalid_form``. If the form
does not validate, it is passed on to the controller through this
argument. The handler of the correct form, in this case
``create_thing``, must have the same signature as the controller,
except for ``invalid_form``, which is replaced with ``form`` in the
signature of the correct handler.

If you want to use the same entry point to show and validate forms of
different kinds, you should use ``verify_post.multi``. This method
accepts a list of form options specified with keyword arguments which
are the names of the forms on the page. The form options have to be
tuples specifying the form for validation and the valid form
handler. Here is an example::

    from django import forms
    from django_drapes import verify_post
    from .models import Thing, Organism

    class ThingForm(forms.Form):
        name = forms.CharField(required=True, min_length=4)
	drape_form_name = forms.CharField(required=True,
                                          widget=forms.HiddenInput(),
					  initial='thing_form')

    class OrganismForm(forms.Form):
        genus = forms.CharField(required=True, min_length=10)
	drape_form_name = forms.CharField(required=True,
                                          widget=forms.HiddenInput(),
					  initial='organism_form')

    def create_thing(request, form):
        Thing(name=form.data['name'])

    def create_organism(request, form):
        Organism(genus=form.data['genus'])

    @verify_post.multi(thing_form=(EntityForm, create_entity),
                       organism_form=(OrganismsForm, create_organism))
    @require(item='can_view')
    def controller(request, item, invalid_form=None):
    	return render_to_response('form_template.html',
	                          dict(form=ThingForm()))

As it can be seen in this example, the hidden field
``drape_form_name`` of a form has to match the keyword argument to
``verify_post`` which specifies how that form should be handled.

One complication for which I couldn't come up with a decent solution
is form validation with a user. In some cases, it is necessary to to
initialize a form class with a user; an example is when a value has to
be unique per user. In these cases, you have to set the keyword
argument ``pass_user`` to ``True`` for ``verify_post.single``, and a
three-element tuple whose last element is ``True`` to
``verify_post.multi``. Let me know in case you have a better solution.

.. _render_with:

render_with
-----------

render_with turns dictionary return values into rendered templates. It
requires a string as argument, signifying either a template path or
json. render_with then calls django.shortcuts.render with the
dictionary-like return value of the controller, and the template
name::

    @render_with('test.htm')
    def controller(request):
        return dict(message='Hello world')

The default template can be overriden by setting a 'template' key in
the return dictionary to the desired template name. render_with also
respects return values which are subclasses of HttpResponse
(e.g. HttpResponseRedirect). If you want to return something else from
your controller, do not use this decorator.

.. _mixing:

Mixing the decorators
---------------------

Any number of these decorators can be applied to the same
controller. The following is posible::

    @render_with('some_template.html')
    @verify(model_inst=ModelValidator(MockModel,
                                      get_by='slug'))
    @require(model_inst='can_view',
             user='is_authenticated')
    @verify_post.single(ThingForm, create_thing)
    def controller(request, model_inst):
        return model_inst.message

The principle here is that if a decorator depends on the conversions
of another, it should come after it.

Template tags
=============

django-drapes comes with two template tags which make it possible to
refer to permission classes, and to render pieces of html from a
model. These tags are if_allowed and modelview.

.. _if_allowed:

if_allowed
----------

``if_allowed`` is a tag which conditionally renders content based on
the outcome of a permission applied to a user. Let's have an example
for a change. Model and permissions::

    from django.db import models
    from django_drapes import ModelPermission

    class Thing(models.Model):
        slug = models.SlugField(unique=True)

    class ThingPermissions(ModelPermission):
        model = Thing

	def can_view(self, user):
	    return user.username == 'horst'

And then in the template which gets rendered with a user and a thing,
you can do the following::

    {% load wherever_you_put_the_tags %}
    {% if_allowed user can_view thing %}
        {{thing.get_absolute_url}}
    {% else %}
        For horst's eyes only
    {% end_if_allowed %}

If your username is not horst, you will see 'For horst's eyes only'.

.. _modelview:

modelview
---------

The other template tag is a helper called ``modelview``. In order to
insert markup representing an aspect of a model, you can subclass
``ModelView``, and set its class attribute model to a django
model. Attributes of this model can later be referred to in a template
using the ``modelview`` template tag::

    from django.db import models
    from django.template.loader import get_template
    from django.template import Context
    from django_drapes import ModelView

    class Thing(models.Model):
        slug = models.SlugField(unique=True)

    class ThingView(ModelView):
        model = MockModel

        def some_view(self, arg1, arg2=None):
            template = get_template('thing_some_view.html')
            #do stuff with arg1 and arg2 ...
            return template.render(Context(dict(thing=self)))

It is advised to use template.render here, since this way you don't
get a response with the full HTTP headers. A nice feature of this
template tag is that it will pass on any arguments you are calling it
with to the view function.

If you want to get the output of a model view outside of a template,
you can use the view function named just ``v`` to get the ModelView
for a model instance::

    from django_drapes import verify, ModelValidator, v
    from .models import Thing

    @verify(thing=ModelValidator(Thing,
                                 get_by='slug'))
    def just_some_view(request, thing):
        return v(thing).some_view()

Registering the template tags
-----------------------------

Since django-drapes is not organized as an app, both of these tags
have to be manually registered to be used in templates. You can do
this by creating a templatetags folder in one of your project apps,
and then including the following in a file there::

    from django import template
    from django_drapes import model_permission, modelview
    register = template.Library()
    register.tag('if_allowed', model_permission)
    register.tag('modelview', modelview)

You are free to change the names of the tags, of course.
