#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This file introduces the observation models that can be used by the Study class for data analysis. An observation model
here referes to a likelihood function, stating the probability of a measurement at a certain time step, given the
parameter values.
"""

import numpy as np

class Poisson:
    """
    Poisson observation model. Subsequent data points are considered independent and distributed according to the
    Poisson distribution. Input data consists of integer values, typically the number of events in a fixed time
    interval. The model has one parameter, often denoted by lambda, which describes the rate of the modeled events.
    """
    def __init__(self):
        self.segmentLength = 1  # number of measurements in one data segment
        self.defaultGridSize = [1000]
        self.defaultBoundaries = [[0, 1]]
        self.uninformativePdf = None

    def __str__(self):
        return 'Poisson'

    def pdf(self, grid, x):
        """
        Probability density function of the Poisson model

        Parameters:
            grid - Parameter grid for discerete rate (lambda) values
            x - Data segment from formatted data (in this case a single number of events)

        Returns:
            Discretized Poisson pdf as numpy array (with same shape as grid)
        """

        # check for missing data
        if np.isnan(x[0]):
            if self.uninformativePdf is not None:
                return self.uninformativePdf  # arbitrary likelihood
            else:
                return np.ones_like(grid[0])/np.sum(np.ones_like(grid[0]))  # uniform likelihood

        return (grid[0]**x[0])*(np.exp(-grid[0]))/(np.math.factorial(x[0]))

class AR1:
    """
    Auto-regressive process of first order. This model describes a simple stochastic time series model with an
    exponential autocorrelation-function. It can be recursively defined as: d_t = r_t * d_(t-1) + s_t * e_t, with d_t
    being the data point at time t, r_t the correlation coefficient of subsequent data points and s_t being the noise
    amplitude of the process. e_t is distributed according to a standard normal distribution.
    """
    def __init__(self):
        self.segmentLength = 2  # number of measurements in one data segment
        self.defaultGridSize = [200, 200]
        self.defaultBoundaries = [[-1, 1], [0, 1]]
        self.uninformativePdf = None

    def __str__(self):
        return 'Autoregressive process of first order (AR1)'

    def pdf(self, grid, x):
        """
        Probability density function of the Auto-regressive process of first order

        Parameters:
            grid - Parameter grid for discerete values of the correlation coefficient and noise amplitude
            x - Data segment from formatted data (in this case a pair of measurements)

        Returns:
            Discretized pdf (for data point d_t, given d_(t-1) and parameters) as numpy array (with same shape as grid).
        """

        # check for missing data
        if np.isnan(x[0]) or np.isnan(x[1]):
            if self.uninformativePdf is not None:
                return self.uninformativePdf  # arbitrary likelihood
            else:
                return np.ones_like(grid[0])/np.sum(np.ones_like(grid[0]))  # uniform likelihood

        return np.exp(-((x[1] - grid[0]*x[0])**2.)/(2.*grid[1]**2.) - np.log(2.*np.pi*grid[1]**2.))
