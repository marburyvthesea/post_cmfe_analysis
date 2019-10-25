#!/usr/bin/env python3.5
# -*- coding: utf-8 -*-
"""
Helper functions to support 'run_cnmfe_matlab.py'

Please see that file for more details.

Created on Nov 1 2017

@author: tamachado@stanford.edu
"""

from past.utils import old_div

from matplotlib import pyplot as plt
import scipy.sparse as sparse
import numpy as np
import miniscope_analysis as ma
from tqdm import tqdm


def align_behavior_data(msCam_timestamps, behavCam_timestamps):
    """returns msCam Df with aligned timestamps
    """
    #lists of ms cam and behavcam time stamps from time_stamps_df 
    behavCam_frames = []
    sys_clock_behavCam = []
    for msCam_frame in tqdm(range(0+1, len(msCam_timestamps)+1)):
        #get sys clock time of each miniscope recorded frame
        #sys_clock_msCam = time_stamps['sysClock'].loc[msCam_frame]
        #find behav cam frame closest to sys clock time of ms frame
        behavCam_frame = list(behavCam_timestamps.iloc[(behavCam_timestamps['sysClock']-msCam_timestamps['sysClock'].loc[msCam_frame]).abs().argsort()[:1]].index)[0]
        behavCam_frames.append(behavCam_frame)
        sys_clock_behavCam.append(behavCam_timestamps.loc[behavCam_frame]['sysClock'])
        
    msCam_timestamps['behavCam_frames'] = behavCam_frames
    msCam_timestamps['sys_clock_behavCam'] = sys_clock_behavCam

    return(msCam_timestamps)



def get_ISIs(signal, framerate, num_cells, event_threshold):
    event_times = []
    event_ISIs = []
    for cell in range(num_cells):
        event_indicies_by_cell = ma.count_events_in_array(signal[cell], 20, .1, threshold=event_threshold, up=True)[1]
        event_times_by_cell = ([(1/framerate)*x for x in event_indicies_by_cell])
        event_times.append(event_times_by_cell)
        cell_ISIs = [(event_times_by_cell[event]-event_times_by_cell[event-1]) for event in range(1, len(event_times_by_cell))]
        event_ISIs.append(cell_ISIs)
    return(event_times, event_ISIs)  

def binning_function_uncrop(bin_increment_samples, z_scored_cell, z_score_threshold):
    bin_start = 0
    bin_end = bin_increment_samples
    binned = np.zeros(len(z_scored_cell))
    #time_index = []
    while bin_end < len(z_scored_cell):
        if np.any(z_scored_cell[bin_start:bin_end]>z_score_threshold):
            binned[bin_start:bin_end] = np.ones(bin_increment_samples)
        else:
            binned[bin_start:bin_end] = np.zeros(bin_increment_samples)
        #time_index.append(bin_start)
        bin_start += bin_increment_samples
        bin_end += bin_increment_samples
    return(np.array(binned))

def binning_function(bin_increment_samples, z_scored_cell, z_score_threshold):
    bin_start = 0
    bin_end = bin_increment_samples
    binned = []
    #time_index = []
    while bin_end < len(z_scored_cell):
        if np.any(z_scored_cell[bin_start:bin_end]>z_score_threshold):
            binned.append(1)
        else:
            binned.append(0)
        #time_index.append(bin_start)
        bin_start += bin_increment_samples
        bin_end += bin_increment_samples
    return(np.array(binned))


def normalize(trace, percentile=True):
    """ Normalize a fluorescence trace by its max or its 99th percentile. """
    trace = trace - np.min(trace)
    if np.percentile(trace, 99) > 0:
        if percentile:
            trace = trace / np.percentile(trace, 99)
        else:
            trace = trace / np.max(trace)
    return trace


def com(A, d1, d2):
    """Calculation of the center of mass for spatial components

       From Caiman: https://github.com/flatironinstitute/CaImAn
       @author: agiovann

     Inputs:
     ------
     A:   np.ndarray
          matrix of spatial components (d x K)

     d1:  int
          number of pixels in x-direction

     d2:  int
          number of pixels in y-direction

     Output:
     -------
     cm:  np.ndarray
          center of mass for spatial components (K x 2)
    """
    nr = np.shape(A)[-1]
    Coor = dict()
    Coor['x'] = np.kron(np.ones((d2, 1)), np.expand_dims(list(range(d1)),
                        axis=1))
    Coor['y'] = np.kron(np.expand_dims(list(range(d2)), axis=1),
                        np.ones((d1, 1)))
    cm = np.zeros((nr, 2))        # vector for center of mass
    cm[:, 0] = old_div(np.dot(Coor['x'].T, A), A.sum(axis=0))
    cm[:, 1] = old_div(np.dot(Coor['y'].T, A), A.sum(axis=0))

    return cm


def plot_contours(A, Cn, list_to_plot=None, thr=None, thr_method='max', maxthr=0.2, nrgthr=0.9,
                  display_numbers=True, max_number=None,
                  cmap=None, swap_dim=False, colors='w', vmin=None,
                  vmax=None, **kwargs):
    """Plots contour of spatial components against a background image
       and returns their coordinates

       From Caiman: https://github.com/flatironinstitute/CaImAn
       @author: agiovann

     Parameters:
     -----------
     A:   np.ndarray or sparse matrix
               Matrix of Spatial components (d x K)

     Cn:  np.ndarray (2D)
               Background image (e.g. mean, correlation)

     list_to_plot: 
      optional input list of specific cells to plot

     thr_method: [optional] string
              Method of thresholding:
                  'max' sets to zero pixels that have value less
                  than a fraction of the max value
                  'nrg' keeps the pixels that contribute up to a
                  specified fraction of the energy

     maxthr: [optional] scalar
                Threshold of max value

     nrgthr: [optional] scalar
                Threshold of energy

     thr: scalar between 0 and 1
               Energy threshold for computing contours (default 0.9)
               Kept for backwards compatibility.
               If not None then thr_method = 'nrg', and nrgthr = thr

     display_number:     Boolean
               Display number of ROIs if checked (default True)

     max_number:    int
               Display the number for only the first max_number components
               (default None, display all numbers)

     cmap:     string
               User specifies the colormap (default None, default colormap)

     Returns:
     --------
     Coor: list of coordinates with center of mass,
        contour plot coordinates and bounding box for each component
    """
    if sparse.issparse(A):
        A = np.array(A.todense())
    else:
        A = np.array(A)

    if swap_dim:
        Cn = Cn.T
        print('Swapping dim')

    d1, d2 = np.shape(Cn)
    d, nr = np.shape(A)
    if max_number is None:
        max_number = nr

    if thr is not None:
        thr_method = 'nrg'
        nrgthr = thr
        warn("The way to call utilities.plot_contours has changed.")

    x, y = np.mgrid[0:d1:1, 0:d2:1]

    ax = plt.gca()
    if vmax is None and vmin is None:
        plt.imshow(Cn, interpolation=None, cmap=cmap,
                   vmin=np.percentile(Cn[~np.isnan(Cn)], 1),
                   vmax=np.percentile(Cn[~np.isnan(Cn)], 99))
    else:
        plt.imshow(Cn, interpolation=None, cmap=cmap,
                   vmin=vmin, vmax=vmax)

    coordinates = []
    cm = com(A, d1, d2)
    
    #switch to accomodate input list of cells to plot
    if list_to_plot:
      to_plot = list_to_plot
    else:
      to_plot = range(np.minimum(nr, max_number))

    for i in to_plot:
        pars = dict(kwargs)
        if thr_method == 'nrg':
            indx = np.argsort(A[:, i], axis=None)[::-1]
            cumEn = np.cumsum(A[:, i].flatten()[indx]**2)
            cumEn /= cumEn[-1]
            Bvec = np.zeros(d)
            Bvec[indx] = cumEn
            thr = nrgthr

        else:
            if thr_method != 'max':
                warn("Unknown threshold method. Choosing max")
            Bvec = A[:, i].flatten()
            Bvec /= np.max(Bvec)
            thr = maxthr

        if swap_dim:
            Bmat = np.reshape(Bvec, np.shape(Cn), order='C')
        else:
            Bmat = np.reshape(Bvec, np.shape(Cn), order='F')
        cs = plt.contour(y, x, Bmat, [thr], colors=colors)

        # this fix is necessary for having disjoint figures and borders
        p = cs.collections[0].get_paths()
        v = np.atleast_2d([np.nan, np.nan])
        for pths in p:
            vtx = pths.vertices
            num_close_coords = np.sum(np.isclose(vtx[0, :], vtx[-1, :]))
            if num_close_coords < 2:
                if num_close_coords == 0:
                    # case angle
                    newpt = np.round(old_div(vtx[-1, :], [d2, d1])) * [d2, d1]
                    vtx = np.concatenate((vtx, newpt[np.newaxis, :]), axis=0)

                else:
                    # case one is border
                    vtx = np.concatenate((vtx, vtx[0, np.newaxis]), axis=0)

            v = np.concatenate((v, vtx, np.atleast_2d([np.nan, np.nan])),
                               axis=0)

        pars['CoM'] = np.squeeze(cm[i, :])
        pars['coordinates'] = v
        pars['bbox'] = [np.floor(np.min(v[:, 1])), np.ceil(np.max(v[:, 1])),
                        np.floor(np.min(v[:, 0])), np.ceil(np.max(v[:, 0]))]
        pars['neuron_id'] = i + 1
        coordinates.append(pars)

    if display_numbers:
        for i in to_plot:
            if swap_dim:
                ax.text(cm[i, 0], cm[i, 1], str(i + 1), color=colors)
            else:
                ax.text(cm[i, 1], cm[i, 0], str(i + 1), color=colors)

    return coordinates
