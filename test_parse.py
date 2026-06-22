from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.test import EnvironBuilder
from flask import Request

builder = EnvironBuilder(method='POST', data={'subjects[]': ['Tafseer', 'Arabic']})
env = builder.get_environ()
req = Request(env)

print("getlist subjects[]:", req.form.getlist('subjects[]'))
print("getlist subjects:", req.form.getlist('subjects'))
