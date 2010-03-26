/*! \file   multinomial.h
 *  \brief  Multinomial.
 *  \author Bryan Silverthorn <bcs@cargo-cult.org>
 */

#ifndef _UTEXAS_STATISTICS_MULTINOMIAL_H_
#define _UTEXAS_STATISTICS_MULTINOMIAL_H_

#include <utexas/python/numpy_array.h>

namespace utexas
{

//! Multinomial distribution.
class Multinomial
{
    public:
        typedef NumpyArrayFY<double, 1> Sample;

    private:
        typedef NumpyArrayFY<double, 1> Beta;

    public:
        //! Construct.
        Multinomial
        (
            Beta beta //!< the distribution parameter vector.
        )
        :
            _beta(beta)
        {
            // FIXME L1 normalization should be optional
            _beta     /= numpy.sum(beta)
            _log_beta  = numpy.nan_to_num(numpy.log(self.__beta))
        }

    public:
        //! Get a norm-1 sample from this distribution.
        Sample variate() const
        {
            return this->variate(1);
        }

        //! Get a sample from this distribution.
        Sample
        variate
        (
            size_t N //!< the L1 norm of the count vectors drawn.
        )
        const
        {
            return scipy.random.multinomial(N, self.__beta)
        }

        //! Get the nonzero dimension of a norm-1 sample.
        size_t indicator() const
        {
            // FIXME.
        }

        //! Return the log likelihood of \p counts under this distribution.
        double
        log_likelihood
        (
            const Sample& sample //!< the sample to consider.
        )
        {
            // sanity
            size_t D = _beta.template d<0>();

            UTEXAS_ASSERT(sample.template d<0>() == D);

            // calculate
            unsigned long n = 0;
            double        l = 0.0;

            for(size_t d = D; d--;)
            {
                n += sample(d);
                l -= ln_gamma(sample(d) + 1);
                l += _log_beta(d) * sample(d);
            }

            return l + ln_gamma(n + 1);
        }

        //! Get the multinomial parameter vector.
        const Beta& get_beta() const
        {
            return _beta;
        }

        //!  Get the log of the multinomial parameter vector.
        const Beta& get_log_beta() const
        {
            return _log_beta;
        }

        // FIXME probably want an assignment operator or two, at least

    private:
        Beta _beta;
        Beta _log_beta;
};

}

#endif

