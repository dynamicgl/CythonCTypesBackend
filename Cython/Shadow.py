# cython.* namespace for pure mode.

compiled = False

_Unspecified = object()

# Function decorators

def _empty_decorator(x):
    return x

def locals(**arg_types):
    return _empty_decorator

def test_assert_path_exists(path):
    return _empty_decorator

def test_fail_if_path_exists(path):
    return _empty_decorator

class _EmptyDecoratorAndManager(object):
    def __call__(self, x):
        return x
    def __enter__(self):
        pass
    def __exit__(self, exc_type, exc_value, traceback):
        pass

cclass = ccall = cfunc = _EmptyDecoratorAndManager()

returns = lambda type_arg: _EmptyDecoratorAndManager()

final = internal = _empty_decorator

def inline(f, *args, **kwds):
  if isinstance(f, basestring):
    from Cython.Build.Inline import cython_inline
    return cython_inline(f, *args, **kwds)
  else:
    assert len(args) == len(kwds) == 0
    return f

def compile(f):
    from Cython.Build.Inline import RuntimeCompiledFunction
    return RuntimeCompiledFunction(f)

# Special functions

def cdiv(a, b):
    q = a / b
    if q < 0:
        q += 1

def cmod(a, b):
    r = a % b
    if (a*b) < 0:
        r -= b
    return r


# Emulated language constructs

def cast(type, *args):
    if hasattr(type, '__call__'):
        return type(*args)
    else:
        return args[0]

def sizeof(arg):
    return 1

def typeof(arg):
    return arg.__class__.__name__
    # return type(arg)

def address(arg):
    return pointer(type(arg))([arg])

def declare(type=None, value=_Unspecified, **kwds):
    if type is not None and hasattr(type, '__call__'):
        if value is not _Unspecified:
            return type(value)
        else:
            return type()
    else:
        return value

class _nogil(object):
    """Support for 'with nogil' statement
    """
    def __enter__(self):
        pass
    def __exit__(self, exc_class, exc, tb):
        return exc_class is None

nogil = _nogil()
gil = _nogil()
del _nogil

# Emulated types

class CythonMetaType(type):

    def __getitem__(type, ix):
        return array(type, ix)

CythonTypeObject = CythonMetaType('CythonTypeObject', (object,), {})

class CythonType(CythonTypeObject):

    def _pointer(self, n=1):
        for i in range(n):
            self = pointer(self)
        return self

class PointerType(CythonType):

    def __init__(self, value=None):
        if isinstance(value, (ArrayType, PointerType)):
            self._items = [cast(self._basetype, a) for a in value._items]
        elif isinstance(value, list):
            self._items = [cast(self._basetype, a) for a in value]
        elif value is None or value == 0:
            self._items = []
        else:
            raise ValueError

    def __getitem__(self, ix):
        if ix < 0:
            raise IndexError("negative indexing not allowed in C")
        return self._items[ix]

    def __setitem__(self, ix, value):
        if ix < 0:
            raise IndexError("negative indexing not allowed in C")
        self._items[ix] = cast(self._basetype, value)

    def __eq__(self, value):
        if value is None and not self._items:
            return True
        elif type(self) != type(value):
            return False
        else:
            return not self._items and not value._items

    def __repr__(self):
        return "%s *" % (self._basetype,)

class ArrayType(PointerType):

    def __init__(self):
        self._items = [None] * self._n


class StructType(CythonType):

    def __init__(self, cast_from=_Unspecified, **data):
        if cast_from is not _Unspecified:
            # do cast
            if len(data) > 0:
                raise ValueError('Cannot accept keyword arguments when casting.')
            if type(cast_from) is not type(self):
                raise ValueError('Cannot cast from %s'%cast_from)
            for key, value in cast_from.__dict__.items():
                setattr(self, key, value)
        else:
            for key, value in data.iteritems():
                setattr(self, key, value)

    def __setattr__(self, key, value):
        if key in self._members:
            self.__dict__[key] = cast(self._members[key], value)
        else:
            raise AttributeError("Struct has no member '%s'" % key)


class UnionType(CythonType):

    def __init__(self, cast_from=_Unspecified, **data):
        if cast_from is not _Unspecified:
            # do type cast
            if len(data) > 0:
                raise ValueError('Cannot accept keyword arguments when casting.')
            if isinstance(cast_from, dict):
                datadict = cast_from
            elif type(cast_from) is type(self):
                datadict = cast_from.__dict__
            else:
                raise ValueError('Cannot cast from %s'%cast_from)
        else:
            datadict = data
        if len(datadict) > 1:
            raise AttributeError("Union can only store one field at a time.")
        for key, value in datadict.iteritems():
            setattr(self, key, value)

    def __setattr__(self, key, value):
        if key in '__dict__':
            CythonType.__setattr__(self, key, value)
        elif key in self._members:
            self.__dict__ = {key: cast(self._members[key], value)}
        else:
            raise AttributeError("Union has no member '%s'" % key)

def pointer(basetype):
    class PointerInstance(PointerType):
        _basetype = basetype
    return PointerInstance

def array(basetype, n):
    class ArrayInstance(ArrayType):
        _basetype = basetype
        _n = n
    return ArrayInstance

def struct(**members):
    class StructInstance(StructType):
        _members = members
    for key in members:
        setattr(StructInstance, key, None)
    return StructInstance

def union(**members):
    class UnionInstance(UnionType):
        _members = members
    for key in members:
        setattr(UnionInstance, key, None)
    return UnionInstance

class typedef(CythonType):

    def __init__(self, type, name=None):
        self._basetype = type
        self.name = name

    def __call__(self, *arg):
        value = cast(self._basetype, *arg)
        return value

    def __repr__(self):
        return self.name or str(self._basetype)

class _FusedType(CythonType):
    pass


def fused_type(*args):
    if not args:
        raise TypeError("Expected at least one type as argument")

    # Find the numeric type with biggest rank if all types are numeric
    rank = -1
    for type in args:
        if type not in (py_int, py_long, py_float, py_complex):
            break

        if type_ordering.index(type) > rank:
            result_type = type
    else:
        return result_type

    # Not a simple numeric type, return a fused type instance. The result
    # isn't really meant to be used, as we can't keep track of the context in
    # pure-mode. Casting won't do anything in this case.
    return _FusedType()


def _specialized_from_args(signatures, args, kwargs):
    "Perhaps this should be implemented in a TreeFragment in Cython code"
    raise Exception("yet to be implemented")


py_int = typedef(int, "int")
try:
    py_long = typedef(long, "long")
except NameError: # Py3
    py_long = typedef(int, "long")
py_float = typedef(float, "float")
py_complex = typedef(complex, "double complex")


# Predefined types

int_types = ['char', 'short', 'Py_UNICODE', 'int', 'long', 'longlong', 'Py_ssize_t', 'size_t']
float_types = ['longdouble', 'double', 'float']
complex_types = ['longdoublecomplex', 'doublecomplex', 'floatcomplex', 'complex']
other_types = ['bint', 'void']

to_repr = {
    'longlong': 'long long',
    'longdouble': 'long double',
    'longdoublecomplex': 'long double complex',
    'doublecomplex': 'double complex',
    'floatcomplex': 'float complex',
}.get

gs = globals()

for name in int_types:
    reprname = to_repr(name, name)
    gs[name] = typedef(py_int, reprname)
    if name != 'Py_UNICODE' and not name.endswith('size_t'):
        gs['u'+name] = typedef(py_int, "unsigned " + reprname)
        gs['s'+name] = typedef(py_int, "signed " + reprname)

for name in float_types:
    gs[name] = typedef(py_float, to_repr(name, name))

for name in complex_types:
    gs[name] = typedef(py_complex, to_repr(name, name))

bint = typedef(bool, "bint")
void = typedef(int, "void")

for t in int_types + float_types + complex_types + other_types:
    for i in range(1, 4):
        gs["%s_%s" % ('p'*i, t)] = globals()[t]._pointer(i)

void = typedef(None, "void")
NULL = p_void(0)

integral = floating = numeric = _FusedType()

type_ordering = [py_int, py_long, py_float, py_complex]

class CythonDotParallel(object):
    """
    The cython.parallel module.
    """

    __all__ = ['parallel', 'prange', 'threadid']

    def parallel(self, num_threads=None):
        return nogil

    def prange(self, start=0, stop=None, step=1, schedule=None, nogil=False):
        if stop is None:
            stop = start
            start = 0
        return range(start, stop, step)

    def threadid(self):
        return 0

    # def threadsavailable(self):
        # return 1

import sys
sys.modules['cython.parallel'] = CythonDotParallel()
del sys

import ctypes
import ctypes.util
def _ctype_find_func(lib_list, func_name):
    for lib_name in lib_list:
        lib_name = lib_name.strip()
        lib = ctypes.CDLL(ctypes.util.find_library(lib_name))
        try:
            getattr(lib, func_name)
            return getattr(lib, func_name)
        except AttributeError:
            pass
        
    raise NameError("Function '%s' cannot be found in libs: %s" % (func_name, lib_list))

def ctypes_func(func_name, libs, restype, *argtypes):
    if isinstance(libs, basestring):
        libs = [libs]

    ctype_func = _ctype_find_func(libs, func_name)
    ctype_func.restype = restype
    
    ctype_func.argtypes = [t for t in argtypes]

    return ctype_func

def ctypes_struct(fields):
    class struct(ctypes.Structure):
        _fields_ = fields
        
    return struct

def ctypes_declare(ctypes_t):        
    return ctypes_t()

class ctypes_extern(object):        
    def __init__(self, include_file):
        self.include_file = include_file
    def __enter__(self, *args):
        pass
    def __exit__(self, *args):
        pass
    

def ctypes_union(fields, size=None):
    if size is not None:
        fields.append(('_pad', ctypes.c_byte*size))
        
    class union(ctypes.Union):
        _fields_ = fields
        
    return union
    
    
    
    