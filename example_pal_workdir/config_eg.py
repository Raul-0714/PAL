""" Configure file
"""
import data_pipeline as dp
import numpy as np

class Config(object):
  def __init__(self):

    # 1. picker params
    self.win_sta    = [0.8,0.4,1.]  # win for STA: det, p, s
    self.win_lta    = [6.,2.,2.]    # win for LTA: det, p, s
    self.win_kurt   = [5.,1.]       # win for kurtosis: long & short
    self.trig_thres = 12.           # threshold to trig picker (by energy)
    self.p_win      = [.5,1.]       # search win for P 
    self.s_win      = 10.           # search win for S 
    self.pca_win    = 1.            # win_len for PCA filter
    self.pca_range  = [0.,2.]       # time range to apply PCA filter
    self.fd_thres   = 2.5           # min value of dominant frequency
    self.amp_win    = [1.,4.]       # time win to get S amplitude
    self.det_gap    = 5.            # time gap between detections
    self.to_prep    = True          # whether to preprocess the raw data
    self.freq_band  = [2,40]        # frequency band 

    # 2. assoc params
    self.min_sta    = 4             # min num of sta to assoc
    self.ot_dev     = 2.            # max time deviation for ot assoc
    self.max_res    = 1.5           # max P res for loc assoc
    self.xy_margin  = 0.1           # xy (lateral) range inferred from sta loc
    self.xy_grid    = 0.02          # xy (lateral) grid size (in degree)
    self.z_grids    = np.arange(2,20,3)  # z (dep) grids
    self.vp         = 5.9           # averaged P velocity

    # 3. data interface
    self.get_data_dict = dp.get_data_dict
    self.get_sta_dict = dp.get_sta_dict
    self.get_picks = dp.get_picks
    self.read_data = dp.read_data

