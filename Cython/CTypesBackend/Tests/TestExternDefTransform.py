from Cython.CTypesBackend.ExternDefTransform import ExternDefTransform
from Cython.Compiler.ParseTreeTransforms import NormalizeTree
from Cython.TestUtils import TransformTest

class TestExternDefTransform(TransformTest):
    def test_func_transform(self):
        t = self.run_pipeline([NormalizeTree(self), ExternDefTransform(["c"])],
u"""\
cdef extern from "stdio.h":
    int printf(char *, int *)\
""")
        self.assertEquals(self.codeToString(t),
"""\
printf = ctypes.CDLL(ctypes.util.find_library('c')).printf
printf.argtypes = [ctypes.c_char_p,ctypes.POINTER(ctypes.c_int),]
printf.restype = ctypes.c_int\
""")

    def test_void_func_transform(self):
        t = self.run_pipeline([NormalizeTree(self), ExternDefTransform(["c"])],
u"""\
cdef extern from "stdio.h":
    void printf(char *, char)\
""")
        self.assertEquals(self.codeToString(t),
u"""\
printf = ctypes.CDLL(ctypes.util.find_library('c')).printf
printf.argtypes = [ctypes.c_char_p,ctypes.c_char,]
printf.restype = None\
""")

    def test_struct_transform(self):
        # Probably platform dependent
        t = self.run_pipeline([NormalizeTree(self), ExternDefTransform(["c"])],
u"""\
cdef extern from "sys/time.h":
    ctypedef struct timeval:
        int tv_sec
        int tv_usec\
""")
        self.assertEquals(self.codeToString(t),
"""\
class timeval(ctypes.Structure,):
    pass
timeval._fields_ = [('tv_sec',ctypes.c_long,),('tv_usec',ctypes.c_long,),]\
""")

if __name__ == "__main__":
    import unittest
    unittest.main()
