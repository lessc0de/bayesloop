#!/usr/bin/env python
"""
This file introduces an extension to the basic Study-class which builds on the change-point transition model.
"""

import numpy as np
from .study import Study
from .preprocessing import *
from .transitionModels import ChangePoint


class ChangepointStudy(Study):
    """
    This class builds on the Study-class and the change-point transition model to perform a series of analyses with varying
    change point times. It subsequently computes the average model from all possible change points and creates a probability
    distribution of change point times.
    """
    def __init__(self):
        super(ChangepointStudy, self).__init__()

        self.changepointPrior = None
        self.changepointDistribution = None
        self.averagePosteriorSequence = None

        print '  --> Change-point study'

    def fit(self, silent=False):
        """
        This method over-rides the according method of the Study-class. It runs the algorithm for all possible change-
        points. The posterior sequence represents the average model of all analyses. Posterior mean values are computed
        from this average model.

        Parameters:
            silent - If set to True, no output is generated by the fitting method.

        Returns:
            None
        """
        if not silent:
            print '+ Started new fit.'

        # prepare arrays for change-point distribution and average posterior sequence
        self.formattedData = movingWindow(self.rawData, self.observationModel.segmentLength)
        if self.changepointPrior is None:
            self.changepointPrior = np.ones(len(self.formattedData))/len(self.formattedData)
        self.averagePosteriorSequence = np.zeros([len(self.formattedData)]+self.gridSize)
        logEvidenceList = []
        localEvidenceList = []

        for tChange in range(len(self.formattedData)):
            # configure transistion model
            K = ChangePoint(tChange=tChange)
            self.setTransitionModel(K, silent=True)

            # call fit method from parent class
            Study.fit(self, silent=True)

            logEvidenceList.append(self.logEvidence)
            localEvidenceList.append(self.localEvidence)
            self.averagePosteriorSequence += self.posteriorSequence*np.exp(self.logEvidence)*self.changepointPrior[tChange]

            if not silent:
                print '    + t = {} -- log10-evidence = {:.5f}'.format(tChange, self.logEvidence / np.log(10))

        # compute average posterior distribution
        normalization = self.averagePosteriorSequence.sum(axis=1)
        self.averagePosteriorSequence /= normalization[:,None]

        # set self.posteriorSequence to average posterior sequence for plotting reasons
        self.posteriorSequence = self.averagePosteriorSequence

        if not silent:
            print '    + Computed average posterior sequence'

        # compute log-evidence of average model
        self.logEvidence = np.log(np.sum(np.exp(np.array(logEvidenceList))*self.changepointPrior))

        if not silent:
            print '    + Log10-evidence of average model: {:.5f}'.format(self.logEvidence / np.log(10))

        # compute change-point distribution
        self.changepointDistribution = np.exp(np.array(logEvidenceList))*self.changepointPrior
        self.changepointDistribution /= np.sum(self.changepointDistribution)

        if not silent:
            print '    + Computed change-point distribution'

        # compute local evidence of average model
        self.localEvidence = np.sum((np.array(localEvidenceList).T*self.changepointDistribution).T, axis=0)

        if not silent:
            print '    + Computed local evidence of average model'

        # compute posterior mean values
        self.posteriorMeanValues = np.empty([len(self.grid), len(self.posteriorSequence)])
        for i in range(len(self.grid)):
            self.posteriorMeanValues[i] = np.array([np.sum(p*self.grid[i]) for p in self.posteriorSequence])

        if not silent:
            print '    + Computed mean parameter values.'

    # optimization methods are inherited from Study class, but cannot be used in this case
    def optimize(self):
        raise AttributeError( "'changepointStudy' object has no attribute 'optimize'" )

    def optimizationStep(self):
        raise AttributeError( "'changepointStudy' object has no attribute 'optimizationStep'" )

    def setHyperParameters(self):
        raise AttributeError( "'changepointStudy' object has no attribute 'setHyperParameters'" )

    def unpackHyperParameters(self):
        raise AttributeError( "'changepointStudy' object has no attribute 'unpackHyperParameters'" )



