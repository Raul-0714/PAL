""" Run picker and associator
    raw waveforms --> picks --> events
"""
import os, glob
import argparse
import numpy as np
from obspy import UTCDateTime
import picker_pal
import associator_pal
import config
import warnings
warnings.filterwarnings("ignore")

if __name__ == '__main__':
    def get_arguments_from_command_line():

        parser = argparse.ArgumentParser()
        parser.add_argument('--data_dir', type=str,
                        default='/data2/ZSY_SAC')
        parser.add_argument('--time_range', type=str,
                        default='20171003-20171004')
        parser.add_argument('--sta_file', type=str,
                        default='input/station.dat')
        parser.add_argument('--out_ctlg', type=str,
                        default='./output/tmp.ctlg')
        parser.add_argument('--out_pha', type=str,
                        default='./output/tmp.pha')
        parser.add_argument('--out_pick_dir', type=str,
                        default='./output/picks')
        args = parser.parse_args()
        return args
    

    arguments = get_arguments_from_command_line()


# PAL config
cfg = config.Config()
get_data_dict = cfg.get_data_dict
read_data = cfg.read_data
sta_dict = cfg.get_sta_dict(arguments.sta_file)
picker = picker_pal.STA_LTA_Kurtosis(\
    win_sta = cfg.win_sta,
    win_lta = cfg.win_lta,
    trig_thres = cfg.trig_thres,
    p_win = cfg.p_win,
    s_win = cfg.s_win,
    pca_win = cfg.pca_win, 
    pca_range = cfg.pca_range,
    fd_thres = cfg.fd_thres,
    amp_win = cfg.amp_win,
    win_kurt = cfg.win_kurt,
    det_gap = cfg.det_gap,
    to_prep = cfg.to_prep,
    freq_band = cfg.freq_band)
associator = associator_pal.TS_Assoc(\
    sta_dict,
    xy_margin = cfg.xy_margin,
    xy_grid = cfg.xy_grid, 
    z_grids = cfg.z_grids,
    min_sta = cfg.min_sta,
    ot_dev = cfg.ot_dev,
    max_res = cfg.max_res,
    vp = cfg.vp)
out_root = os.path.split(arguments.out_ctlg)[0]
if not os.path.exists(out_root): os.makedirs(out_root)
if not os.path.exists(arguments.out_pick_dir): os.makedirs(arguments.out_pick_dir)
out_ctlg = open(arguments.out_ctlg,'w')
out_pha = open(arguments.out_pha,'w')


def get_time_range():
    return [UTCDateTime(date) for date in arguments.time_range.split('-')]


start_date, end_date = get_time_range()


def print_time_range():
    print('run pick & assoc: raw_waveform --> picks --> events')
    print('time range: {} to {}'.format(start_date.date, end_date.date))


print_time_range()

def get_date_of_day_x(start_date, x_days_after_start_date):
    day_in_sec = 86400
    date = start_date + x_days_after_start_date * day_in_sec

    return date

# for all days
num_days = (end_date.date - start_date.date).days
for day_x in range(num_days):
    # get data paths
    date = get_date_of_day_x(start_date, day_x)
    
    data_dict = get_data_dict(date, arguments.data_dir)
    todel = [net_sta for net_sta in data_dict if net_sta not in sta_dict]
    for net_sta in todel: data_dict.pop(net_sta)
    if data_dict=={}: continue
    # 1. phase picking: waveform --> picks
    fpick_path = os.path.join(arguments.out_pick_dir, str(date.date)+'.pick')
    out_pick = open(fpick_path,'w')
    for i, data_filename_list in enumerate(data_dict.values()):
        print('-'*40)
        stream = read_data(data_filename_list, sta_dict)
        picks_i = picker.pick(stream, out_pick)
        picks = picks_i if i==0 else np.append(picks, picks_i)
    out_pick.close()
    # 2. associate picks: picks --> event_picks & event_loc
    associator.associate(picks, out_ctlg, out_pha)




# finish making catalog
out_pha.close()
out_ctlg.close()
