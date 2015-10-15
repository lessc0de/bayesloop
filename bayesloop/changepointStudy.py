#!/usr/bin/env python
"""
This file introduces an extension to the basic Study-class which builds on the change-point transition model.
"""

import numpy as np
from .rasterStudy import *
from .preprocessing import *
from .helper import flatten


class ChangepointStudy(RasterStudy):
    """
    This class builds on the RasterStudy-class and the change-point transition model to perform a series of analyses
    with varying change point times. It subsequently computes the average model from all possible change points and
    creates a probability distribution of change point times. It supports any number of change-points and arbitarily
    combined models.
    """
    def __init__(self):
        super(ChangepointStudy, self).__init__()

        # store all possible combinations of change-points (even the ones that are assigned a probability of zero),
        # to reconstruct change-point distribution after analysis
        self.allRasterValues = []
        self.mask = []  # mask to select valid change-point combinations
        print '  --> Change-point analysis'

    def fit(self, raster=[], forwardOnly=False, evidenceOnly=False, silent=False):
        """
        This method over-rides the according method of the Raster Study-class. It runs the algorithm for all possible
        combinations of change-points (and possible scans a range of values for other hyper-parameters). The posterior
        sequence represents the average model of all analyses. Posterior mean values are computed from this average
        model.

        Parameters:
            raster - While the class ChangepointStudy automatically iterates over all possible combinations of
                     change-points, it is possible to provide an additional list of lists with each containing the name
                     of a hyper-parameter together with a lower and upper boundary as well as a number of steps in
                     between.
                     Example: raster = [['sigma', 0, 1, 20],['log10pMin', -10, -5, 10]]

            forwardOnly - If set to True, the fitting process is terminated after the forward pass. The resulting
                posterior distributions are so-called "filtering distributions" which - at each time step -
                only incorporate the information of past data points. This option thus emulates an online
                analysis.

            evidenceOnly - If set to True, only forward pass is run and evidence is calculated. In contrast to the
                forwardOnly option, no posterior mean values are computed and no posterior distributions are stored.

            silent - If set to True, no output is generated by the fitting method.

        Returns:
            None
        """
        # format data once, so number of data segments is known
        self.formattedData = movingWindow(self.rawData, self.observationModel.segmentLength)

        # check for 'tChange' hyper-parameters in transition model
        hyperParameterNames = list(flatten(self.unpackHyperParameters(self.transitionModel)))
        nChangepoint = hyperParameterNames.count('tChange')

        # check for 'tBreak' hyper-parameter in transition model
        nBreakpoint = 0
        if hyperParameterNames.count('tBreak') > 1:
            print '! Multiple instances of SerialTransition models are currently not supported by ChangepointStudy.'
            return
        if hyperParameterNames.count('tBreak') == 1:
            temp = self.selectedHyperParameters[:]  # temporarily store selected hyper-parameters to restore later
            self.selectedHyperParameters = ['tBreak']
            nBreakpoint = len(self.unpackSelectedHyperParameters())

        if nChangepoint == 0 and nBreakpoint == 0:
            print '! No change-points or break-points detected in transition model. Check transition model.'
            return

        # using both types is not supported at the moment
        if nChangepoint > 0 and nBreakpoint > 0:
            print '! Detected both change-points (Changepoint transition model) and break-points ' \
                  '  (SerialTransitionModel). Currently, only one type is supported in a single ' \
                  '  transition model.'
            return

        # create raster in the case of change-points
        if nChangepoint > 0:
            print '+ Detected {} change-point(s) in transition model.'.format(nChangepoint)
            if raster:
                print '+ {} additional hyper-parameter(s) specified for rastering.'.format(len(raster))

            # build custom raster of change-point values (have to be ordered) +
            # standard raster for other hyper-parameters
            self.raster = [['tChange', 0, len(self.formattedData)-1, len(self.formattedData)]]*nChangepoint + raster
            temp = np.meshgrid(*[np.linspace(lower, upper, steps) for name, lower, upper, steps in self.raster])
            self.allRasterValues = np.array([t.flatten() for t in temp]).T  # all value tuples

            # only accept if change-point values are ordered (and not equal)
            self.mask = np.array([all(x[i] < x[i+1] for i in range(nChangepoint-1)) for x in self.allRasterValues],
                                 dtype=bool)
            self.rasterValues = self.allRasterValues[self.mask]

            # set raster constant
            self.rasterConstant = [1]*nChangepoint + [np.abs(upper-lower)/(float(steps)-1) for
                                                      name, lower, upper, steps in raster]

        # create raster in the case of break-points
        if nBreakpoint > 0:
            print '+ Detected {} break-point(s) in transition model.'.format(nBreakpoint)
            if raster:
                print '+ Additional {} hyper-parameters specified for rastering.'.format(len(raster))

            # build custom raster of change-point values (have to be ordered) +
            # standard raster for other hyper-parameters
            self.raster = [['tBreak', 0, len(self.formattedData)-1, len(self.formattedData)]]*nBreakpoint + raster
            temp = np.meshgrid(*[np.linspace(lower, upper, steps) for name, lower, upper, steps in self.raster])
            self.allRasterValues = np.array([t.flatten() for t in temp]).T  # all value tuples

            # only accept if change-point values are ordered (and not equal)
            self.mask = np.array([all(x[i] < x[i+1] for i in range(nBreakpoint-1)) for x in self.allRasterValues],
                                 dtype=bool)
            self.rasterValues = self.allRasterValues[self.mask]

            # set raster constant
            self.rasterConstant = [1]*nBreakpoint + [np.abs(upper-lower)/(float(steps)-1) for
                                                     name, lower, upper, steps in raster]

            # redefine self.raster, such that 'tBreak' only occurs once (is passed as list)
            self.raster = [['tBreak', 0, len(self.formattedData)-1, len(self.formattedData)]] + raster

        # call fit method of raster-study
        RasterStudy.fit(self, forwardOnly=forwardOnly, evidenceOnly=evidenceOnly, customRaster=True, silent=silent)

        # for break-points, self.raster has to be restored to original value after fitting
        # (containing multiple 'tBreak', for proper plotting)
        if nBreakpoint > 0:
            self.raster = [['tBreak', 0, len(self.formattedData)-1, len(self.formattedData)]]*nBreakpoint + raster

        # for proper plotting, rasterValues must include all possible combinations of hyper-parameter values. We
        # therefore have to include invalid combinations and assign the probability zero to them.
        temp = np.zeros(len(self.allRasterValues))
        temp[self.mask] = self.hyperParameterDistribution
        self.hyperParameterDistribution = temp

    def plotChangepointDistribution(self, idx=0, tRange=[], **kwargs):
        """
        Creates a bar chart of a change-point distribution done with the ChangepointStudy class. The distribution is
        marginalized with respect to the specific change-point passed by index (first change-point of the transition
        model: idx=0).

        Parameters:
            idx - Index of the change-point to be analyzed (default: 0 (first change-point))

            tRange - A list containing a lower and an upper boundary for the times displayed in the plots.
                     (can be used to display e.g. years instead of time steps)

            **kwargs - All further keyword-arguments are passed to the bar-plot (see matplotlib documentation)

        Returns:
            Two numpy arrays. The first array contains the change-point times, the second one the corresponding
            probability values
        """
        if tRange and len(tRange) != 2:
            print '! A lower AND upper boundary for the time range have to be provided.'
            tRange = []

        # self.raster has to be temporarily altered to display custom times
        if tRange:
            temp = self.raster[:]
            self.raster[idx][1] = tRange[0]
            self.raster[idx][2] = tRange[1]

        x, marginalDistribution = RasterStudy.plotHyperParameterDistribution(self, param=idx, **kwargs)
        plt.xlabel('change-point #{}'.format(idx+1))

        # restore self.raster if necessary
        if tRange:
            self.raster = temp

        return x, marginalDistribution

    def plotBreakpointDistribution(self, idx=0, tRange=[], **kwargs):
        """
        Creates a bar chart of a break-point distribution done with the ChangepointStudy class. The distribution is
        marginalized with respect to the specific break-point passed by index (first break-point of the transition
        model: idx=0).

        Parameters:
            idx - Index of the break-point to be analyzed (default: 0 (first break-point))

            tRange - A list containing a lower and an upper boundary for the times displayed in the plots.
                     (can be used to display e.g. years instead of time steps)

            **kwargs - All further keyword-arguments are passed to the bar-plot (see matplotlib documentation)

        Returns:
            Two numpy arrays. The first array contains the break-point times, the second one the corresponding
            probability values
        """
        if tRange and len(tRange) != 2:
            print '! A lower AND upper boundary for the time range have to be provided.'
            tRange = []

        # self.raster has to be temporarily altered to display custom times
        if tRange:
            temp = self.raster[:]
            self.raster[idx][1] = tRange[0]
            self.raster[idx][2] = tRange[1]

        x, marginalDistribution = RasterStudy.plotHyperParameterDistribution(self, param=idx, **kwargs)
        plt.xlabel('break-point #{}'.format(idx+1))

        # restore self.raster if necessary
        if tRange:
            self.raster = temp

        return x, marginalDistribution

    def plotJointChangepointDistribution(self, indices=[0, 1], tRange=[], figure=None, subplot=111, **kwargs):
        """
        Creates a 3D bar chart of a joint change-point distribution (of two change-points) done with the
        ChangepointStudy class. The distribution is marginalized with respect to the change-points passed by their
        indices. Note that the 3D plot can only be included in an existing plot by passing a figure object and subplot
        specification.

        Parameters:
            indices - List of two indices of change-points to display; default: [0, 1]
                      (first and second change-point of the transition model)

            tRange - A list containing a lower and an upper boundary for the times displayed in the plots.
                     (can be used to display e.g. years instead of time steps)

            figure - In case the plot is supposed to be part of an existing figure, it can be passed to the method.
                     By default, a new figure is created.

            subplot - Characterization of subplot alignment, as in matplotlib. Default: 111

            **kwargs - all further keyword-arguments are passed to the bar3d-plot (see matplotlib documentation)

        Returns:
            Three numpy arrays. The first and second array contains the change-point times, the third one the
            corresponding probability (density) values
        """
        if tRange and len(tRange) != 2:
            print '! A lower AND upper boundary for the time range have to be provided.'
            tRange = []

        # self.raster has to be temporarily altered to display custom times
        if tRange:
            temp = self.raster[:]
            for i in indices:
                self.raster[i][1] = tRange[0]
                self.raster[i][2] = tRange[1]

        x, y, marginalDistribution = RasterStudy.plotJointHyperParameterDistribution(self,
                                                                                     params=indices,
                                                                                     figure=figure,
                                                                                     subplot=subplot, **kwargs)
        plt.xlabel('change-point #{}'.format(indices[0]+1))
        plt.ylabel('change-point #{}'.format(indices[1]+1))

        # restore self.raster if necessary
        if tRange:
            self.raster = temp

        return x, y, marginalDistribution

    def plotJointBreakpointDistribution(self, indices=[0, 1], tRange=[], figure=None, subplot=111, **kwargs):
        """
        Creates a 3D bar chart of a joint break-point distribution (of two break-points) done with the
        ChangepointStudy class. The distribution is marginalized with respect to the break-points passed by their
        indices. Note that the 3D plot can only be included in an existing plot by passing a figure object and subplot
        specification.

        Parameters:
            indices - List of two indices of break-points to display; default: [0, 1]
                      (first and second break-point of the transition model)

            tRange - A list containing a lower and an upper boundary for the times displayed in the plots.
                     (can be used to display e.g. years instead of time steps)

            figure - In case the plot is supposed to be part of an existing figure, it can be passed to the method.
                     By default, a new figure is created.

            subplot - Characterization of subplot alignment, as in matplotlib. Default: 111

            **kwargs - all further keyword-arguments are passed to the bar3d-plot (see matplotlib documentation)

        Returns:
            Three numpy arrays. The first and second array contains the break-point times, the third one the
            corresponding probability (density) values
        """
        if tRange and len(tRange) != 2:
            print '! A lower AND upper boundary for the time range have to be provided.'
            tRange = []

        # self.raster has to be temporarily altered to display custom times
        if tRange:
            temp = self.raster[:]
            for i in indices:
                self.raster[i][1] = tRange[0]
                self.raster[i][2] = tRange[1]

        x, y, marginalDistribution = RasterStudy.plotJointHyperParameterDistribution(self,
                                                                                     params=indices,
                                                                                     figure=figure,
                                                                                     subplot=subplot,
                                                                                     **kwargs)
        plt.xlabel('break-point #{}'.format(indices[0]+1))
        plt.ylabel('break-point #{}'.format(indices[1]+1))

        # restore self.raster if necessary
        if tRange:
            self.raster = temp

        return x, y, marginalDistribution

    def plotDuration(self, indices=[0, 1], returnDistribution=False, **kwargs):
        """
        Creates a histogram for the number of time steps between two change/break-points. This distribution of duration
        is created from the joint distribution of the two specified change/break-points.

        Parameters:
            indices - List of two indices of change/break-points to display; default: [0, 1]
                (first and second change/break-point of the transition model)

            returnDistribution - If set to True, this function returns a numpy array containing all probability
                (density) values of the duration distribution

            **kwargs - All further keyword-arguments are passed to the bar-plot (see matplotlib documentation)

        Returns:
            Numpy array containing all probability (density) values of the duration distribution
        """
        hyperParameterNames = [name for name, lower, upper, steps in self.raster]

        # check if exactly two indices are provided
        if not len(indices) == 2:
            print '! Exactly two change/break-points have to be specified ([0, 1]: first two change/break-points).'
            return

        axesToMarginalize = range(len(hyperParameterNames))
        for p in indices:
            axesToMarginalize.remove(p)

        # reshape hyper-parameter distribution for easy marginalizing
        rasterSteps = [steps for name, lower, upper, steps in self.raster]
        distribution = self.hyperParameterDistribution.reshape(rasterSteps)
        marginalDistribution = np.squeeze(np.apply_over_axes(np.sum, distribution, axesToMarginalize))

        # marginal distribution is not created by sum, but by the integral
        integrationFactor = np.prod([self.rasterConstant[axis] for axis in axesToMarginalize])
        marginalDistribution *= integrationFactor

        # compute distribution over number of time steps between the two change/break-times
        durationDistribution = np.zeros(marginalDistribution.shape[0])
        for i in range(marginalDistribution.shape[0]):
            for j in range(marginalDistribution.shape[1]):
                durationDistribution[abs(i-j)] += marginalDistribution[i, j]

        # plot result
        plt.bar(range(marginalDistribution.shape[0]), durationDistribution, align='center', width=1, **kwargs)

        plt.xlabel('duration between point #{} and #{} (in time steps)'.format(indices[0]+1, indices[1]+1))
        plt.ylabel('probability')

        return durationDistribution

