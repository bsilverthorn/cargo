"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

import numpy

from llvm.core import (
    Type,
    Builder,
    Constant,
    )
from cargo.llvm.high_level import (
    high,
    HighFunction,
    )

class Binomial(object):
    """
    Build low-level operations of the binomial distribution.

    Relevant types:
    - parameter : {float64 p; uint32 n;}
    - sample    : uint32
    """

    def __init__(self, estimation_n = None, epsilon = 0.0):
        """
        Initialize.
        """

        self._parameter_dtype = numpy.dtype([("p", numpy.float64), ("n", numpy.uint32)])
        self._sample_dtype    = numpy.dtype(numpy.int32)
        self._estimation_n    = estimation_n # XXX MASSIVE HACK; needs to go away
        self._epsilon         = epsilon

    def get_emitter(self, module):
        """
        Return IR emitter.
        """

        return BinomialEmitter(self, module)

    @property
    def parameter_dtype(self):
        """
        Type of the distribution parameter.
        """

        return self._parameter_dtype

    @property
    def sample_dtype(self):
        """
        Type of the distribution sample.
        """

        return self._sample_dtype

class BinomialEmitter(object):
    """
    Build low-level operations of the binomial distribution.
    """

    def __init__(self, model, module):
        """
        Initialize.
        """

        # members
        self._model  = model
        self._module = module

        # link the GSL
        import ctypes

        from ctypes      import CDLL
        from ctypes.util import find_library

        CDLL(find_library("cblas"), ctypes.RTLD_GLOBAL)
        CDLL(find_library("gsl"  ), ctypes.RTLD_GLOBAL)

    def ll(self, parameter, sample, out):
        """
        Compute log probability under this distribution.
        """

        from ctypes import c_uint

        log = HighFunction("log"                 , float, [float                ])
        pdf = HighFunction("gsl_ran_binomial_pdf", float, [c_uint, float, c_uint])

        log(
            pdf(
                sample.data.load(),
                parameter.data.gep(0, 0).load(),
                parameter.data.gep(0, 1).load(),
                ),
            ) \
            .store(out)

    def ml(self, samples, weights, out):
        """
        Emit computation of the estimated maximum-likelihood parameter.
        """

        from cargo.llvm import this_builder

        compute = \
            HighFunction(
                "binomial_ml",
                Type.void(),
                [samples.data.type_, weights.data.type_, out.data.type_],
                new = True,
                )
        entry = compute.low.append_basic_block("entry")

        with this_builder(Builder.new(entry)) as builder:
            self._ml(
                samples.using(compute.arguments[0]),
                weights.using(compute.arguments[1]),
                out.using(compute.arguments[2]),
                )

            builder.ret_void()

        compute(samples.data, weights.data, out.data)

    def _ml(self, samples, weights, out):
        """
        Emit computation of the estimated maximum-likelihood parameter.
        """

        total_k = high.stack_allocate(float, 0.0)
        total_w = high.stack_allocate(float, 0.0)

        @high.for_(samples.shape[0])
        def _(n):
            weight = weights.at(n).data.load()
            sample = samples.at(n).data.load().cast_to(float)

            (total_k.load() + sample * weight).store(total_k)
            (total_w.load() + weight * float(self._model._estimation_n)).store(total_w)

        final_ratio = \
              (total_k.load() + self._model._epsilon) \
            / (total_w.load() + self._model._epsilon)

        final_ratio.store(out.data.gep(0, 0))
        high.value(self._model._estimation_n).store(out.data.gep(0, 1))

class MixedBinomial(object):
    """
    The "mixed binomial" distribution.

    Relevant types:
    - parameter : float64 p
    - sample    : {uint32 k; uint32 n;}
    """

    def __init__(self, epsilon = 1e-3):
        """
        Initialize.
        """

        self._epsilon         = epsilon
        self._parameter_dtype = numpy.dtype(numpy.float64)
        self._sample_dtype    = numpy.dtype([("k", numpy.uint32), ("n", numpy.uint32)])

    def get_emitter(self, module):
        """
        Return IR emitter.
        """

        return MixedBinomialEmitter(self, module)

    @property
    def parameter_dtype(self):
        """
        Type of the distribution parameter.
        """

        return self._parameter_dtype

    @property
    def sample_dtype(self):
        """
        Type of the distribution sample.
        """

        return self._sample_dtype

class MixedBinomialEmitter(object):
    """
    Build low-level operations of the binomial distribution.
    """

    def __init__(self, model, module):
        """
        Initialize.
        """

        self._model  = model
        self._module = module

        # link the GSL
        import ctypes

        from ctypes      import CDLL
        from ctypes.util import find_library

        CDLL(find_library("cblas"), ctypes.RTLD_GLOBAL)
        CDLL(find_library("gsl"  ), ctypes.RTLD_GLOBAL)

    def ll(self, parameter, sample, out):
        """
        Compute log probability under this distribution.
        """

        from ctypes import c_uint

        log = HighFunction("log"                 , float, [float                ])
        pdf = HighFunction("gsl_ran_binomial_pdf", float, [c_uint, float, c_uint])

        log(
            pdf(
                sample.data.gep(0, 0).load(),
                parameter.data.load(),
                sample.data.gep(0, 1).load(),
                ),
            ) \
            .store(out)

    def ml(self, samples, weights, out):
        """
        Emit computation of the estimated maximum-likelihood parameter.
        """

        from cargo.llvm import this_builder

        compute = \
            HighFunction(
                "mixed_binomial_ml",
                Type.void(),
                [samples.data.type_, weights.data.type_, out.data.type_],
                new = True,
                )
        entry = compute.low.append_basic_block("entry")

        with this_builder(Builder.new(entry)) as builder:
            self._ml(
                samples.using(compute.arguments[0]),
                weights.using(compute.arguments[1]),
                out.using(compute.arguments[2]),
                )

            builder.ret_void()

        compute(samples.data, weights.data, out.data)

    def _ml(self, samples, weights, out):
        """
        Emit computation of the estimated maximum-likelihood parameter.
        """

        import math

        total_k = high.stack_allocate(float, 0.0)
        total_n = high.stack_allocate(float, 0.0)

        @high.for_(samples.shape[0])
        def _(n):
            weight   = weights.at(n).data.load()
            sample_k = samples.at(n).data.gep(0, 0).load().cast_to(float)
            sample_n = samples.at(n).data.gep(0, 1).load().cast_to(float)

            (total_k.load() + sample_k * weight).store(total_k)
            (total_n.load() + sample_n * weight).store(total_n)

            @high.python(total_k.load(), total_n.load())
            def _(k_py, n_py):
                if isnan(k_py) or isnan(n_py):
                    print "k", k_py, "n", n_py

        final_ratio = \
              (total_k.load() + self._model._epsilon) \
            / (total_n.load() + self._model._epsilon)

        final_ratio.store(out.data)

