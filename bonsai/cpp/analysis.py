
#Copyright (c) 2017 Andre Santos
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

###############################################################################
# Imports
###############################################################################

from .model import CppEntity, CppBlock, CppControlFlow, CppExpression, \
                   CppFunction, CppFunctionCall, CppOperator, \
                   CppReference, CppVariable


###############################################################################
# AST Analysis
###############################################################################

class CppQuery(object):
    def __init__(self, cppobj):
        assert isinstance(cppobj, CppEntity)
        self.root = cppobj
        self.cls = None
        self.recursive = False
        self.attributes = {}

    @property
    def references(self):
        self.cls = CppReference
        self.recursive = False
        return self

    @property
    def all_references(self):
        self.cls = CppReference
        self.recursive = True
        return self

    @property
    def calls(self):
        self.cls = CppFunctionCall
        self.recursive = False
        return self

    @property
    def all_calls(self):
        self.cls = CppFunctionCall
        self.recursive = True
        return self

    def where_name(self, name):
        self.attributes["name"] = name
        return self

    def where_result(self, result):
        self.attributes["result"] = result
        return self

    def get(self):
        result = []
        for cppobj in self.root.filter(self.cls, recursive = self.recursive):
            passes = True
            for key, value in self.attributes.iteritems():
                if isinstance(value, basestring):
                    if getattr(cppobj, key) != value:
                        passes = False
                else:
                    if not getattr(cppobj, key) in value:
                        passes = False
            if passes:
                result.append(cppobj)
        return result


###############################################################################
# Interface Functions
###############################################################################

def resolve_expression(expression):
    assert isinstance(expression, CppExpression.TYPES)
    if isinstance(expression, CppReference):
        return resolve_reference(expression)
    if isinstance(expression, CppOperator):
        args = []
        for arg in expression.arguments:
            arg = resolve_expression(arg)
            if not isinstance(arg, CppExpression.LITERALS):
                return expression
            args.append(arg)
        if expression.is_binary:
            a = args[0]
            b = args[1]
            if not isinstance(a, CppExpression.LITERALS) \
                    or not isinstance(b, CppExpression.LITERALS):
                return expression
            if expression.name == "+":
                return a + b
            if expression.name == "-":
                return a - b
            if expression.name == "*":
                return a * b
            if expression.name == "/":
                return a / b
            if expression.name == "%":
                return a % b
    # if isinstance(expression, CppExpression.LITERALS):
    # if isinstance(expression, SomeCpp):
    # if isinstance(expression, CppFunctionCall):
    # if isinstance(expression, CppDefaultArgument):
    return expression


def resolve_reference(reference):
    assert isinstance(reference, CppReference)
    if reference.statement is None:
        return None # TODO investigate
    si = reference.statement._si
    if (reference.reference is None
            or isinstance(reference.reference, basestring)):
        return None
    if isinstance(reference.reference, CppVariable):
        var = reference.reference
        value = var.value
        function = reference.function
        for w in var.writes:
            ws = w.statement
            if not w.function is function:
                continue
            if ws._si < si:
                if w.arguments[0].reference is var:
                    value = resolve_expression(w.arguments[1])
                else:
                    continue # TODO
            elif ws._si == si:
                if w.arguments[0] is reference:
                    value = resolve_expression(w.arguments[1])
                else:
                    continue # TODO
        if value is None and var.is_parameter:
            calls = [call for call in function.references \
                          if isinstance(call, CppFunctionCall)]
            if len(calls) != 1:
                return None
            i = function.parameters.index(var)
            if len(calls[0].arguments) <= i:
                return None
            arg = calls[0].arguments[i]
            if isinstance(arg, CppReference):
                return resolve_reference(arg)
            return arg
        if isinstance(value, CppExpression.TYPES):
            return resolve_expression(value)
        return value
    return reference.reference


def is_under_control_flow(cppobj, recursive = False):
    return get_control_depth(cppobj, recursive) > 0


def get_control_depth(cppobj, recursive = False):
    depth = 0
    while not cppobj is None:
        if (isinstance(cppobj, CppBlock)
                and isinstance(cppobj.parent, CppControlFlow)):
            depth += 1
        elif isinstance(cppobj, CppFunction):
            if recursive:
                calls = [get_control_depth(call) for call in cppobj.references
                                if isinstance(call, CppFunctionCall)]
                if calls:
                    depth += max(calls)
            return depth
        cppobj = cppobj.parent
    return depth