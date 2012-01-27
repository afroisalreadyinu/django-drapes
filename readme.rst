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
when that does not work. The conversions are specified as keyword
arguments with a validator matching the name of the controller
argument. The validators have to match the formencode library
validator format.

The values for the conversions are searched in the arguments for the
controller function, and additionally the get parameters if the
request is a get. This causes a mismatch between the url
definition and the function signature, since one can't specify get
parameters in a url entry, and a controller normally has to look up a
get parameter in the get dict. Because of this mismatch, the
controller has to include a keyword argument that defaults to an
unused value in order to force its conversion from the get parameter
into an argument. If you want the GET dictionary to be included in
verification, the first argument of the controller has to be called
request.

require
-------

require is a decorator for checking permissions on an incoming request
to a controller. It accepts keyword arguments referring either to user
(accessed through request.user) or the positional or keyword arguments
of a view function, and a string corresponding to the permission. The
request is assumed to be the first argument of the controller. What
permission to execute is determined in the following order:

- An attribute of the object
- A method of the object
- A method of the model permission (a subclass of ModelPermission;
  see below) that accepts a user as argument.

verify_post
-----------

verify_post is used to check the validity of forms.

render_with
-----------
render_with turns dictionary return values into rendered templates.


Template tags
=============

if_allowed and modelview
