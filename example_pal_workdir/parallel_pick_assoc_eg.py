import os, shutil
from obspy import UTCDateTime
# create a time_range class with start_date and end_date along with functions that can access the data

class TimeRange:
    def __init__(self, time_range_inString):
        self.start_date = UTCDateTime(time_range_inString.split('-')[0])
        self.end_date = UTCDateTime(time_range_inString.split('-')[1])

    def get_start_date(self):
        return self.start_date

    def get_end_date(self):
        return self.end_date
    

# parallel params
pal_dir = '/home/zhouyj/software/PAL'
#shutil.copyfile('config_eg.py', os.path.join(pal_dir, 'config.py'))
data_dir = '/data/Example_data'
time_range = TimeRange('20190704-20190707')
sta_file = 'input/example_pal_format1.sta'
num_workers = 3
out_root = 'output/eg'
out_pick_dir = 'output/eg/picks'


def split_timeRange_into_subRange(time_range, num_workers):
    sub_ranges = []
    dt = calculate_time_step(time_range, num_workers)
    for woker_x in range(num_workers):
        sub_ranges.append(calculate_range_for_worker_id(time_range, woker_x, dt))

    return sub_ranges


def calculate_time_step(time_range, num_workers):
    return (time_range.get_end_date() - time_range.get_start_date())/num_workers


def calculate_range_for_worker_id(time_range, worker_id, dt):
    return '{}-{}'.format(calculate_start_date(time_range, worker_id, dt), calculate_end_date(time_range, worker_id, dt))


def calculate_start_date(time_range, worker_id, dt):
    return ''.join(str((time_range.get_start_date() + worker_id*dt).date).split('-'))


def calculate_end_date(time_range, worker_id, dt):
    return ''.join(str((time_range.get_start_date() + (worker_id+1)*dt).date).split('-'))


sub_time_ranges = split_timeRange_into_subRange(time_range, num_workers)

def assign_work_to_workers(sub_time_range, num_workers):
    for worker_x in range(num_workers):
        assign_work(sub_time_range[worker_x])


def assign_work(time_range):
    output_dir = set_output_dir(time_range)
    run_picker_and_associator(time_range, output_dir)


def set_output_dir(time_range):
    out_phase_dir = '{}/phase_{}'.format(out_root, time_range)
    out_ctlg_dir = '{}/catalog_{}'.format(out_root, time_range)

    return out_phase_dir, out_ctlg_dir


def run_picker_and_associator(time_range, output_dir):
    command = generate_command(time_range, output_dir)
    os.system(command)


def generate_command(time_range, output_dir):
    command = "python {}/run_pick_assoc.py \
        --time_range={} --data_dir={} --sta_file={} \
        --out_pick_dir={} --out_ctlg={} --out_pha={}" \
        .format(pal_dir, time_range, data_dir, sta_file, out_pick_dir, output_dir[1], output_dir[0])

    return command


assign_work_to_workers(sub_time_ranges, num_workers)


"""for worker_id in range(num_workers):
    t0 = ''.join(str((time_range.get_start_date() + worker_id*time_range_for_each_worker).date).split('-'))
    t1 = ''.join(str((time_range.get_start_date() + (worker_id+1)*time_range_for_each_worker).date).split('-'))
    time_range_inString = '{}-{}'.format(t0, t1)
    print(time_range_inString)
    out_pha = '{}/phase_{}.dat'.format(out_root, time_range_inString)
    out_ctlg = '{}/catalog_{}.dat'.format(out_root, time_range_inString)
    os.system("python {}/run_pick_assoc.py \
        --time_range={} --data_dir={} --sta_file={} \
        --out_pick_dir={} --out_ctlg={} --out_pha={} & " \
        .format(pal_dir, time_range_inString, data_dir, sta_file, out_pick_dir, out_ctlg, out_pha)) """
    
