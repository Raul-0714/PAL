import numpy as np
import data_pipeline as dp


class STA_LTA_PCA(object):

  """ STA/LTA based P&S Picker
    trigger picker: Z chn STA/LTA reach trig_thres
    --> pick P: find within p_win
    --> pick S: PCA filter & find winthin s_win
  Inputs
    stream: obspy.stream obj (3 chn, [e, n, z])
    pick_win: win len for STA/LTA ([lwin, swin])
    trig_thres: threshold to trig picker
    pick_thres: threshold for picking (0 to 1.)
    p_win: win len for pick detected P
    s_win: win len for S arrivla searching
    pca_win: time win for calc pca filter
    pca_range: time range for pca filter
    fd_trhes: minimum value of dominant frequency
    amp_win: time win to get S amplitude
    det_gap: time gap between detections
    to_prep: whether preprocess stream
    freq_band: frequency band for phase picking
    *note: all time-related params are in sec
  Outputs
    all picks in the stream, and header info
  Usage
    import pickers
    picker = pickers.STA_LTA_PCA()
    picks = picker.pick(stream)
  """

  def __init__(self, 
               pick_win   = [10., 1.],
               trig_thres = 15.,
               pick_thres = 0.96,
               p_win      = [1., 1.],
               s_win      = [0., 20.],
               pca_win    = 1.,
               pca_range  = [0., 2.5],
               fd_thres   = 2.5,
               amp_win    = [1.,5.],
               det_gap    = 5.,
               to_prep    = True,
               prep_func  = dp.preprocess,
               freq_band  = ['highpass',1.]):

    self.pick_win   = pick_win
    self.trig_thres = trig_thres
    self.pick_thres = pick_thres
    self.p_win      = p_win
    self.s_win      = s_win
    self.pca_win    = pca_win
    self.pca_range  = pca_range
    self.fd_thres   = fd_thres
    self.amp_win    = amp_win
    self.det_gap    = det_gap
    self.to_prep    = to_prep
    self.preprocess = prep_func
    self.freq_band  = freq_band


  def pick(self, stream, out_file=None):
    # set output format
    dtype = [('net_sta','O'),
             ('sta_ot','O'),
             ('tp','O'),
             ('ts','O'),
             ('s_amp','O'),
             ('p_snr','O'),
             ('s_snr','O'),
             ('freq_dom','O')]
    # preprocess & extract data
    if self.to_prep: stream = self.preprocess(stream, self.freq_band)
    if len(stream)!=3: return np.array([], dtype=dtype)
    min_npts = min([len(trace) for trace in stream])
    st_data = np.array([trace.data[0:min_npts] for trace in stream])
    # get header
    head = stream[0].stats
    net_sta = '.'.join([head.network, head.station])
    self.samp_rate = head.sampling_rate
    start_time, end_time = head.starttime, head.endtime
    # sec to points
    self.pick_win_npts  = [int(self.samp_rate * win) for win in self.pick_win]
    self.p_win_npts     = [int(self.samp_rate * win) for win in self.p_win]
    self.s_win_npts     = [int(self.samp_rate * win) for win in self.s_win]
    self.pca_win_npts   =  int(self.samp_rate * self.pca_win)
    self.pca_range_npts = [int(self.samp_rate * win) for win in self.pca_range]
    amp_win_npts        = [int(self.samp_rate * win) for win in self.amp_win]
    det_gap_npts        =  int(self.samp_rate * self.det_gap)

    # pick P and S
    picks = []
    # 1. trig picker
    print('1. triggering phase picker')
    cf_trig = self.calc_cf(st_data[2], self.pick_win_npts)
    trig_ppk = np.where(cf_trig > self.trig_thres)[0]
    slide_idx = 0
    # 2. phase picking
    print('2. picking phase:')
    for _ in trig_ppk:
        # 2.1 pick P around idx_trig
        idx_trig = trig_ppk[slide_idx]
        if idx_trig < self.p_win_npts[0] + self.pick_win_npts[0]: 
            slide_idx += 1; continue
        data_p = st_data[2][idx_trig - self.p_win_npts[0] - self.pick_win_npts[0]
                           :idx_trig + self.p_win_npts[1] + self.pick_win_npts[1]]
        cf_p = self.calc_cf(data_p, self.pick_win_npts)
        idx_p = idx_trig - self.pick_win_npts[0] - self.p_win_npts[0] + \
                np.where(cf_p >= self.pick_thres * np.amax(cf_p))[0][0]
        tp = start_time + idx_p / self.samp_rate

        # 2.2 pick S between tp and tp+s_win
        # calc cf on EN chn
        if len(st_data[0]) < idx_p + self.s_win_npts[1]: break
        s_range = [idx_p - self.s_win_npts[0] - self.pick_win_npts[0],
                   idx_p + self.s_win_npts[1] + self.pick_win_npts[1]]
        data_s = np.sqrt(st_data[0][s_range[0] : s_range[1]]**2\
                       + st_data[1][s_range[0] : s_range[1]]**2)
        cf_s = self.calc_cf(data_s, self.pick_win_npts)
        # trig S picker and pick
        pca_filter = self.calc_pca_filter(st_data, idx_p)
        data_s[self.pick_win_npts[0] : self.pick_win_npts[0] + len(pca_filter)] *= pca_filter
        s_trig = np.argmax(data_s[self.pick_win_npts[0]:]) + self.pick_win_npts[0]
        s_range_0 = min(s_trig, int(s_trig + self.pick_win_npts[0])//2)
        s_range_1 = max(s_trig, int(s_trig + self.pick_win_npts[0])//2)
        if s_range_0==s_range_1: s_range_1+=1
        cf_s = cf_s[s_range_0 : s_range_1]
        idx_s = idx_p - self.pick_win_npts[0] - self.s_win_npts[0] + s_range_0 + np.argmax(cf_s)
        ts = start_time + idx_s / self.samp_rate

        # 2.3 get related S amplitude
        amp = self.get_amp(st_data[:,idx_p-amp_win_npts[0] : idx_s+amp_win_npts[1]])
        # 2.4 get p_anr and s_anr
        p_snr = np.amax(cf_p)
        s_snr = np.amax(cf_s)
        # 2.5 calc dominant frequency
        t0 = min(tp, ts)
        t1 = min(tp+(ts-tp)/2, end_time)
        st = stream.slice(t0,t1)
        fd = max([self.calc_freq_dom(tr.data) for tr in st])
        # output
        print('{}, {}, {}'.format(net_sta, tp, ts))
        if tp<ts and fd>self.fd_thres:
            sta_ot = self.calc_ot(tp, ts)
            picks.append((net_sta, sta_ot, tp, ts, amp, p_snr, s_snr, fd))
            if out_file: 
                pick_line = '{},{},{},{},{},{:.2f},{:.2f},{:.2f}\n'\
                    .format(net_sta, sta_ot, tp, ts, amp, p_snr, s_snr, fd)
                out_file.write(pick_line)
        # next detected phase
        rest_det = np.where(trig_ppk > max(idx_trig,idx_s,idx_p) + det_gap_npts)[0]
        if len(rest_det)==0: break
        slide_idx = rest_det[0]
    # convert to structed np.array
    return np.array(picks, dtype=dtype)


  def calc_cf(self, data, win_len):
    """  calc character function (STA/LTA) for a single trace
    Inputs
      data (np.array): input trace data
      win_len (in points): win len for STA/LTA, [lwin, swin]
    Outputs
      cf: character function
    """
    lwin, swin = win_len
    npts = len(data)
    if npts<lwin+swin:
        print('input data too short!')
        return np.zeros(1)
    sta = np.zeros(npts)
    lta = np.ones(npts)
    # use energy
    data = np.cumsum(data**2)
    # Compute the STA and the LTA
    sta[:-swin] = data[swin:] - data[:-swin]
    sta /= swin
    lta[lwin:]  = data[lwin:] - data[:-lwin]
    lta /= lwin
    # Pad zeros (same out size as data)
    sta[:lwin] = 0
    cf = sta/lta
    # avoid bad points
    cf[np.isinf(cf)] = 0.
    cf[np.isnan(cf)] = 0.
    return cf


  def calc_pca_filter(self, data, idx_p):
    """ calc S filter by PCA
    Inputs:
      data (np.array): input 3-chn data
      idx_p (data points): idx for P in data
    Outputs:
      pca_filter (np.array): pca filter for P wave filtering
    """
    p_mat = data[:, idx_p : idx_p + self.pca_win_npts]
    p_r, p_evec = self.calc_pol(p_mat)
    # calc filter
    idx_range = range(idx_p - self.s_win_npts[0] - self.pca_range_npts[0],
                      idx_p - self.s_win_npts[0] + self.pca_range_npts[1])
    pca_filter = np.zeros(len(idx_range))
    for i, idx in enumerate(idx_range):
        s_mat = data[:, idx : idx + self.pca_win_npts]
        s_r, s_evec = self.calc_pol(s_mat)
        u11 = abs(np.dot(p_evec, s_evec))
        pca_filter[i] = 1 - s_r * u11
    return pca_filter


  def calc_pol(self, mat):
    """ calc polarization by PCA
    Inputs
      mat: 3-chn time win (matrix)
    Outputs
      r: polirization degree
      vec: dominant eig-vector
    """
    cov = np.cov(mat)
    e_val, e_vec = np.linalg.eig(cov)
    # calc pol degree
    lam1  = np.amax(e_val)
    lam23 = np.sum(e_val) - lam1
    r = 1 - (0.5 * lam23 / lam1)
    # calc dom vec
    vec = e_vec.T[np.argmax(e_val)]
    return r, vec


  # calculate origin time
  def calc_ot(self, tp, ts):
    vp, vs = 5.9, 3.4
    d = (ts-tp) / (1/vs - 1/vp)
    tt_p = d / vp
    return tp - tt_p


  # get S amplitide
  def get_amp(self, velo, samp_rate=None):
    samp_rate = samp_rate if samp_rate else self.samp_rate
    # remove mean
    velo -= np.reshape(np.mean(velo, axis=1), [velo.shape[0],1])
    # velocity to displacement
    disp = np.cumsum(velo, axis=1)
    disp /= samp_rate
    return np.amax(np.sum(disp**2, axis=0))**0.5


  # calc dominant frequency
  def calc_freq_dom(self, data):
    npts = len(data)
    if npts//2==0: return 0
    data -= np.mean(data)
    psd = abs(np.fft.fft(data))**2
    psd = psd[:npts//2]
    return np.argmax(psd) * self.samp_rate / npts

