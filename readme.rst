=============
django-drapes
=============

django-drapes is a small library to ease authorization and user input
verification. Most of the functionality is packed into decorators
intended for applying to views, hence the name django-drapes.

Decorators
==========

verify
------

The verify decorator turns values passed to the controller into a more
usable form, and throws exceptions in case input does not match the
given validators.

require
-------

The require decorator checks permissions.

verify_post
-----------

verify_post is used to check the validity of forms.

render_with
-----------
render_with turns dictionary return values into rendered templates.


Template tags
=============

if_allowed and modelview
