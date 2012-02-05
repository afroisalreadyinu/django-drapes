import unittest
import json
import formencode
from mock import Mock, patch
import os

from django.template import TemplateSyntaxError
from django.http import HttpResponseRedirect
from django_drapes import (require,
                           verify,
                           verify_post,
                           _build_args_dict,
                           _call_wrapped_func,
                           _perm_to_bool,
                           PermissionException,
                           MultipleValidationErrors,
                           NonmatchingHandlerArgspecs,
                           ModelView,
                           ModelViewNode,
                           modelview,
                           ModelValidator,
                           ModelPermission,
                           ModelPermissionNode,
                           model_permission,
                           render_with,
                           is_json,
                           v,
                           NoSuchView)

class Bunch(dict):

    def __init__(self, *args, **kwargs):
        super(Bunch, self).__init__(self, *args, **kwargs)
        self.__dict__ = self


class FakeForm(object):

    def __init__(self, data_dict=None):
        self.valid = data_dict.get('valid')

    def is_valid(self):
        return self.valid


class HelpersTests(unittest.TestCase):

    def test_argspec(self):
        def func(first_arg, second_arg, third_arg='third_arg_val'):
            pass
        args_dict = _build_args_dict(func,
                                     'first_arg_val',
                                     'second_arg_val',
                                     third_arg='what now?')
        self.failUnlessEqual(args_dict,
                             {'first_arg': 'first_arg_val',
                              'second_arg': 'second_arg_val',
                              'third_arg': 'what now?'})


    def test_perm_to_bool_attribute(self):
        x = Bunch(a_permission=True)
        self.failUnless(_perm_to_bool(x, object(), 'a_permission'))
        x = Bunch(a_permission=False)
        self.failIf(_perm_to_bool(x, object(), 'a_permission'))


    def test_perm_to_bool_method(self):
        class DummyModel(object):
            def a_permission(self):
                return True
        self.failUnless(_perm_to_bool(DummyModel(),
                                      None,
                                      'a_permission'))

        class DummyModel(object):
            def a_permission(self):
                return False
        self.failIf(_perm_to_bool(DummyModel(),
                                  None,
                                  'a_permission'))


    def test_perm_to_bool_lambda(self):
        x = [1,2]
        self.failUnless(_perm_to_bool(x,
                                      None,
                                      lambda z: len(z) == 2))
        x = [1,2]
        self.failIf(_perm_to_bool(x,
                                  None,
                                  lambda z: len(z) == 3))


    def test_call_wrapped_func(self):
        def testing(x, y, z=10):
            self.failUnless(all([x == 1, y == 2, z == 15]))
        _call_wrapped_func(dict(z=15, y=2, x=1), testing)



class PermisionsTests(unittest.TestCase):

    def test_simple_permission_true(self):
        @require(user='attribute_permission')
        def controller(request, an_arg):
            return an_arg
        user = Bunch(attribute_permission=True)
        self.failUnlessEqual(controller(Bunch(user=user), 'test'),
                             'test')


    def test_simple_permission_false(self):
        @require(user='attribute_permission')
        def controller(request, an_arg):
            return an_arg
        user = Bunch(attribute_permission=False)
        self.failUnlessRaises(PermissionException,
                              controller, Bunch(user=user), 0)


    def test_callable_permission_true(self):
        @require(user='callable_permission')
        def controller(request, an_arg):
            return an_arg
        class FakeUser(object):
            def callable_permission(self):
                return True
        self.failUnlessEqual(controller(Bunch(user=FakeUser()), 'test'),
                              'test')


    def test_callable_permission_false(self):
        @require(user='callable_permission')
        def controller(request, an_arg):
            return an_arg
        class FakeUser(object):
            def callable_permission(self):
                return False

        self.failUnlessRaises(PermissionException,
                              controller, Bunch(user=FakeUser()), None)



class ModelPermisionsTests(unittest.TestCase):

    TEST_VAL = "Proper return value"


    def test_model_attribute(self):

        class TestModel(object):
            pass
        dummy_user = object()
        class TestPermission(ModelPermission):
            model = TestModel
            can_view = True

        @require(model_arg='can_view')
        def controller(request, model_arg):
            return self.TEST_VAL

        self.failUnlessEqual(controller(Bunch(user=dummy_user),
                                        TestModel()),
                             self.TEST_VAL)


    def test_permission_not_applicable(self):

        class TestModel(object):
            pass
        dummy_user = object()
        class TestPermission(ModelPermission):
            model = TestModel

        @require(model_arg='can_view')
        def controller(request, model_arg):
            return self.TEST_VAL

        self.failUnlessRaises(ValueError,
                              controller, Bunch(user=dummy_user), TestModel())

    def test_model_permission_true(self):

        class TestModel(object):
            pass
        dummy_user = object()
        class TestPermission(ModelPermission):
            model = TestModel
            def can_has_allowed(self, user):
                return user is dummy_user

        @require(model_arg='can_has_allowed')
        def controller(request, model_arg):
            return self.TEST_VAL

        self.failUnlessEqual(controller(Bunch(user=dummy_user),
                                        TestModel()),
                             self.TEST_VAL)


    def test_model_permission_false(self):

        class TestModel(object):
            pass

        class TestPermission(ModelPermission):
            model = TestModel

            def can_has_not_allowed(self, user):
                return False

        @require(model_arg='can_has_not_allowed')
        def controller(request, model_arg):
            return self.TEST_VAL

        self.failUnlessRaises(PermissionException,
                              controller,
                              Bunch(user=None),
                              TestModel())



class VerifyTests(unittest.TestCase):

    class MockRequest(object):
        method = ""

    def test_validation(self):
        @verify(an_arg=formencode.validators.Int())
        def controller(request, an_arg):
            return an_arg
        self.failUnlessEqual(controller(self.MockRequest(),'10'),
                             10)

    def test_validation_wrong(self):
        @verify(an_arg=formencode.validators.Int())
        def controller(request, an_arg):
            pass
        self.failUnlessRaises(formencode.Invalid,
                              controller, self.MockRequest(), 'HE MAN')

    def test_kw_validation(self):
        @verify(kw_arg=formencode.validators.Int())
        def controller(request, an_arg, kw_arg=None):
            return kw_arg
        self.failUnlessEqual(controller(self.MockRequest(), None, '10'),
                             10)


    def test_kw_validation_wrong(self):
        @verify(kw_arg=formencode.validators.Int())
        def controller(etc, an_arg, kw_arg=None):
            pass
        self.failUnlessRaises(formencode.Invalid,
                              controller, self.MockRequest(), None, 'SHE RA')


    def test_get_parameter_validation_true(self):
        @verify(an_arg=formencode.validators.Int(),
                get_param=formencode.validators.MinLength(3))
        def controller(request, an_arg, get_param=None):
            return get_param
        class MockGetRequest(object):
            method = 'GET'
            GET = dict(get_param='Battle Cat')
        self.failUnlessEqual(controller(MockGetRequest(), None),
                             'Battle Cat')


    def test_get_parameter_validation_false(self):
        @verify(an_arg=formencode.validators.Int(),
                get_param=formencode.validators.MinLength(10))
        def controller(request, an_arg, get_param=None):
            return get_param
        class MockGetRequest(object):
            method = 'GET'
            GET = dict(get_param='Orco')
        self.failUnlessRaises(formencode.Invalid,
                              controller, MockGetRequest(), None)


    def test_get_dict_mixed_with_kwarg(self):

        class MockGetRequest(object):
            method = 'GET'
            GET = {'some_arg':'duncan@grayskull.com'}

        @verify(other_arg=formencode.validators.Int(),
                some_arg=formencode.validators.Email())
        def controller(request, some_arg=None, other_arg=20):
            return some_arg, other_arg

        self.failUnlessEqual(controller(MockGetRequest(), other_arg='10'),
                             ('duncan@grayskull.com', 10))


    def test_mixed_true(self):
        @verify(third=formencode.validators.Int(),
                second=formencode.validators.Email(),
                first=formencode.validators.MinLength(3))
        def controller(first, second, third=None):
            return first, second, third
        self.failUnlessEqual(controller('Cringer', 'teela@grayskull.com', '10'),
                             ('Cringer', 'teela@grayskull.com', 10))


    def test_mixed_false(self):
        @verify(third=formencode.validators.Int(),
                second=formencode.validators.Email(),
                first=formencode.validators.MinLength(3))
        def func(first, second, third=None):
            pass
        self.failUnlessRaises(MultipleValidationErrors,
                              func, '12', 'nota.valid.email', 'not_an_int')
        try:
            func('12', 'nota.valid.email', 'not_an_int')
        except MultipleValidationErrors, error_list:
            self.failUnlessEqual(len(error_list.errors), 3)


class VerifyPostTest(unittest.TestCase):

    def test_signature_check_invalid(self):
        request = Bunch(method='GET')
        def valid_handler(request, form):
            pass
        deco = verify_post.single(None, valid_handler)
        def controller(request, controller_arg, invalid_form=None):
            return "Response"
        self.failUnlessRaises(NonmatchingHandlerArgspecs,
                              deco, controller)


    def test_simple_get(self):
        request = Bunch(method='GET')
        def valid_handler(request, form):
            pass
        @verify_post.single(None, valid_handler)
        def controller(request, invalid_form=None):
            return "Response"
        self.failUnlessEqual(controller(request),
                             "Response")


    def test_correct_post(self):
        request = Bunch(method="POST",
                        POST=dict(valid=True))

        def valid_controller(request, form):
            self.failUnless(form.is_valid())
            return "Valid controller"

        @verify_post.single(FakeForm, valid_controller)
        def controller(request, invalid_form=None):
            return "Original controller"

        self.failUnlessEqual(controller(request),
                             "Valid controller")


    def test_incorrect_post(self):
        request = Bunch(method="POST",
                        POST=dict(valid=False))

        def valid_controller(request, form):
            return "Valid controller"

        @verify_post.single(FakeForm, valid_controller)
        def controller(request, invalid_form=None):
            return "Original controller"

        self.failUnlessEqual(controller(request),
                             "Original controller")


    def test_pass_user(self):
        class FakeForm(object):
            def __init__(self, data_dict, user):
                self.data_dict, self.user = data_dict, user
            def is_valid(self): return True

        request = Bunch(method="POST",
                        POST=dict(),
                        user=Bunch(username="Skeletor"))

        def valid_controller(request, form):
            return "The name is " + form.user.username

        @verify_post.single(FakeForm, valid_controller, pass_user=True)
        def controller(request, invalid_form=None):
            pass

        self.failUnlessEqual(controller(request),
                             "The name is Skeletor")


    def test_correct_post_multiple(self):
        request = Bunch(method="POST",
                        POST=dict(valid=True,
                                  drape_form_name='form1'))

        def valid_controller(request, form):
            self.failUnless(form.is_valid())
            return "Valid controller"

        def invalid_controller(request, form):
            return "Not the valid controller"

        @verify_post.multi(form1=(FakeForm, valid_controller),
                           form2=(FakeForm, invalid_controller))
        def controller(request, form1=None, form2=None):
            return "Original controller"

        self.failUnlessEqual(controller(request),
                             "Valid controller")


    def test_invalid_multiple_post(self):
        request = Bunch(method="POST",
                        POST=dict(valid=False,
                                  drape_form_name='form1'))

        def valid_controller(request, form):
            pass

        @verify_post.multi(form1=(FakeForm, valid_controller),
                           form2=(FakeForm, valid_controller))
        def controller(request, form1=None, form2=None):
            self.failIf(form1 is None)
            return "Original controller"

        self.failUnlessEqual(controller(request),
                             "Original controller")


    def test_multiple_post_pass_user(self):
        dummy_user = object()
        request = Bunch(method="POST",
                        user=dummy_user,
                        POST=dict(valid=False,
                                  drape_form_name='form1'))

        def valid_controller(request, form):
            pass

        def valid_controller_two(request, form):
            self.failUnless(form.user is dummy_user)

        class FakeFormWithUser(object):
            def __init__(self, data_dict, user):
                self.data_dict, self.user = data_dict, user
            def is_valid(self): return True

        @verify_post.multi(form1=(FakeForm, valid_controller),
                           form2=(FakeFormWithUser, valid_controller_two, True))
        def controller(request, form1=None, form2=None):
            return "Original controller"

        self.failUnlessEqual(controller(request),
                             "Original controller")



class CombinedTests(unittest.TestCase):


    def test_verify_and_require(self):

        class MockManager(object):
            def filter(self, *args, **kwargs):
                slug = kwargs.pop('slug')
                return [MockModel(slug)]

        class MockModel(object):
            objects = MockManager()
            def __init__(self, slug):
                self.message = "The slug is: " + slug

        class MockPermission(ModelPermission):
            model = MockModel
            def can_view(self, user):
                return user.username == "Man-at-arms"

        class MockRequest(object):
            method = "GET"
            GET = dict()
            user = Bunch(is_authenticated=True,
                         username="Man-at-arms")

        @verify(model_inst=ModelValidator(MockModel,
                                          get_by='slug'))
        @require(model_inst='can_view',
                 user='is_authenticated')
        def controller(request, model_inst):
            return model_inst.message

        self.failUnlessEqual(controller(MockRequest(), "Ratatazong"),
                             "The slug is: Ratatazong")


class ModelValidatorTests(unittest.TestCase):

    def test_get_by(self):

        class MockManager(object):
            def filter(self, *args, **kwargs):
                some_field_value = kwargs.pop('some_field')
                return [MockModel(some_field_value)]

        class MockModel(object):
            objects = MockManager()
            def __init__(self, field_value):
                self.message = "Field value: " + field_value

        validator = ModelValidator(MockModel, 'some_field')
        self.failUnlessEqual(validator.to_python('field value').message,
                             'Field value: field value')


    def test_no_instances(self):

        class MockManager(object):
            def filter(self, *args, **kwargs):
                return []

        class MockModel(object):
            objects = MockManager()

        validator = ModelValidator(MockModel, 'some_field')
        self.failUnlessRaises(formencode.Invalid,
                              validator.to_python,
                              'field value')


    def test_multiple_instances(self):

        class MockManager(object):
            def filter(self, *args, **kwargs):
                return [MockModel(), MockModel()]

        class MockModel(object):
            objects = MockManager()

        validator = ModelValidator(MockModel, 'some_field')
        self.failUnlessRaises(formencode.Invalid,
                              validator.to_python,
                              'field value')

class DummyResponse(object):
    def __init__(self, response, response_type):
        self.response = response
        self.response_type = response_type

class RenderWithTests(unittest.TestCase):

    def setUp(self):
        import django_drapes
        def render(request, template_name, response_dict):
            try:
                return "%s:%d" % (template_name,
                                  len(response_dict))
            except TypeError:
                return response_dict.__class__
        django_drapes.render = render
        django_drapes.HttpResponse = DummyResponse

    def test_http_response_returned(self):
        #not the optimal test, but there was no easy way around it
        class HttpResponseRedirect(DummyResponse):
            def __init__(self, path):
                pass
        response = HttpResponseRedirect('/')
        @render_with('')
        def controller(request):
            return response
        real_response = controller(Bunch(method='GET',
                                         GET=dict()))
        self.failUnless(real_response is response)


    def test_template_returned(self):
        @render_with('test.htm')
        def controller(request):
            return dict()
        self.failUnlessEqual(controller(Bunch(method='GET',GET=dict())),
                             "test.htm:0")


    def test_template_in_dict_preferred(self):
        @render_with('test.htm')
        def controller(request):
            return dict(template='not_test.htm')
        self.failUnlessEqual(controller(Bunch(method='GET',GET=dict())),
                             "not_test.htm:1")

    def test_is_json_get(self):
        request = Bunch(method="GET",
                        GET=dict(json='true'))
        self.failUnless(is_json(request))
        request = Bunch(method="GET",
                        GET=dict())
        self.failIf(is_json(request))


    def test_is_json_post(self):
        request = Bunch(method="POST",
                        POST=dict(json='true'))
        self.failUnless(is_json(request))
        request = Bunch(method="POST",
                        POST=dict())
        self.failIf(is_json(request))

    def test_render_with_json(self):
        @render_with('json')
        def controller(request):
            return dict(test=True)
        http_response = controller(None)
        json_response = json.loads(http_response.response)
        self.failUnless(json_response['test'])
        self.failUnlessEqual(http_response.response_type,
                             'application/javascript')


    def test_render_nondict_with_json(self):
        @render_with('json')
        def controller(request):
            return [1,2,3]
        http_response = controller(None)
        json_response = json.loads(http_response.response)
        self.failUnless(json_response, [1,2,3])
        self.failUnlessEqual(http_response.response_type,
                             'application/javascript')


    def test_render_template_in_dict_with_json(self):
        @render_with('json')
        def controller(request):
            return dict(template='not_test.htm')
        self.failUnlessEqual(controller(Bunch(method='GET',GET=dict())),
                             "not_test.htm:1")


class ModelViewTests(unittest.TestCase):

    def test_model_view_get_for_model(self):
        class MockModel(Bunch):
            pass

        class MockModelView(ModelView):
            model = MockModel

        self.failUnlessEqual(type(ModelView.get_for_model(MockModel())),
                             MockModelView)

    def test_model_view_v_function(self):
        class MockModel(Bunch):
            pass

        class MockModelView(ModelView):
            model = MockModel

        self.failUnlessEqual(v(MockModel(message='haha')).message,
                             'haha')


    @patch('django.template.Variable')
    def test_model_view_node(self, Variable):
        parser = Mock()
        token = Mock(spec=['split_contents'])
        token.split_contents.return_value = ('model_view', 'model_inst', 'some_view')
        node = modelview(parser, token)
        self.failUnlessEqual(node.model, Variable.return_value)
        self.failUnlessEqual(node.viewname, 'some_view')


    @patch('django.template.Variable')
    def test_model_view_rendering_callable(self, Variable):
        class MockModel(object):
            pass
        class MockModelView(ModelView):
            model = MockModel
            def some_view(self):
                return "Output of some view"
        template_model = Mock()
        template_model.resolve.return_value = MockModel()
        Variable.return_value = template_model
        node = ModelViewNode('instance', 'some_view')
        context = Mock()
        self.failUnlessEqual(node.render(context),
                             'Output of some view')


    @patch('django.template.Variable')
    def test_model_view_rendering_attribute(self, Variable):
        class MockModel(object):
            pass
        class MockModelView(ModelView):
            model = MockModel

            @property
            def some_view(self):
                return "Output of some view"

        template_model = Mock()
        template_model.resolve.return_value = MockModel()
        Variable.return_value = template_model
        node = ModelViewNode('instance', 'some_view')
        context = Mock()
        self.failUnlessEqual(node.render(context),
                             'Output of some view')

    @patch('django.template.Variable')
    def test_raises_exception_on_invalid_view_name(self, Variable):
        class MockModel(object):
            pass
        class MockModelView(ModelView):
            model = MockModel
            def some_view(self):
                return "Output of some view"
        template_model = Mock()
        template_model.resolve.return_value = MockModel()
        Variable.return_value = template_model
        node = ModelViewNode('instance', 'some_other_view')
        context = Mock()
        self.failUnlessRaises(NoSuchView,
                              node.render,
                              context)

    def test_arglist_parsing(self):
        rest_args = ['one', 'two', 'three="haha"', "four=hehe"]
        args, kwargs = ModelViewNode.parse_arg_list(rest_args)
        self.failUnlessEqual(args, ['one', 'two'])
        self.failUnlessEqual(kwargs, dict(three='"haha"',
                                          four="hehe"))


    @patch('django.template.Variable')
    def test_passing_args(self, Variable):
        class MockModel(object):
            pass
        class MockModelView(ModelView):
            model = MockModel
            def some_view(self, first_arg, second_arg=None):
                return "%s %s" % (first_arg, second_arg)

        class MockObject(object):
            pass

        template_model = Mock()
        template_model.resolve.return_value = MockModel()

        return_vals = [template_model, 'variable value']
        def popit(_):
            return return_vals.pop()
        Variable.side_effect = popit
        node = ModelViewNode('instance',
                             'some_view',
                             args=["'some string'"],
                             kwargs=dict(second_arg='otherthing'))
        context = Mock()
        self.failUnlessEqual(node.render(context),
                             'some string variable value')


    def test_args_list_length(self):
        parser = Mock()
        token = Mock(spec=['split_contents'])
        token.split_contents.return_value = ('model_instance',
                                             'model_view')
        self.failUnlessRaises(TemplateSyntaxError,
                              modelview, parser, token)


class ModelPermissionTests(unittest.TestCase):

    @patch('django.template.Variable')
    def test_model_permission_node(self, Variable):
        parser = Mock()
        token = Mock(spec=['split_contents'])
        token.split_contents.return_value = ('if_allowed', 'user', 'some_perm', 'model_inst')
        node = model_permission(parser, token)
        self.failUnlessEqual(node.model_instance, Variable.return_value)
        self.failUnlessEqual(node.permission_name, 'some_perm')


    def test_args_list_length(self):
        parser = Mock()
        token = Mock(spec=['split_contents'])
        token.split_contents.return_value = ('if_allowed', 'user', 'some_perm')
        self.failUnlessRaises(TemplateSyntaxError,
                              model_permission, parser, token)


    @patch('django.template.Variable')
    def test_model_permission_rendering_true(self, Variable):
        class MockUser(object):
            username = "Some username"
        class MockModel(object):
            pass
        class MockModelPermission(ModelPermission):
            model = MockModel
            def can_do_stuff(self, user):
                return user.username == "Some username"

        user_var = Mock(spec=['resolve'])
        user_var.resolve.return_value = MockUser()

        model_var = Mock(spec=['resolve'])
        model_var.resolve.return_value = MockModel()

        variables = [model_var, user_var]
        def side_effect(_):
            return variables.pop()
        Variable.side_effect = side_effect

        nodelist_true = Mock()
        nodelist_true.render.return_value = "True nodelist"

        node = ModelPermissionNode(None, 'can_do_stuff', None, nodelist_true, None)
        context = Mock()
        self.failUnlessEqual(node.render(context),
                             'True nodelist')



    @patch('django.template.Variable')
    def test_model_permission_rendering_false(self, Variable):
        class MockUser(object):
            username = "Some username"
        class MockModel(object):
            pass
        class MockModelPermission(ModelPermission):
            model = MockModel
            def can_do_stuff(self, user):
                return user.username != "Some username"

        user_var = Mock(spec=['resolve'])
        user_var.resolve.return_value = MockUser()

        model_var = Mock(spec=['resolve'])
        model_var.resolve.return_value = MockModel()

        variables = [model_var, user_var]
        def side_effect(_):
            return variables.pop()
        Variable.side_effect = side_effect

        nodelist_false = Mock()
        nodelist_false.render.return_value = "False nodelist"

        node = ModelPermissionNode(None, 'can_do_stuff', None, None, nodelist_false)
        context = Mock()
        self.failUnlessEqual(node.render(context),
                             'False nodelist')

if __name__ == "__main__":
    os.popen("nosetests tests.py --with-coverage --cover-package=django_drapes --cover-html")
