import numpy as np

#ev = open("./sample_events/20190211203348712_0.hst", "rb")
# this seems to correspond to regular file:
# https://ncnr.nist.gov/ncnrdata/view/nexus-hdf-viewer.html?pathlist=ncnrdata+vsans+201902+25309+data&filename=sans27334.nxs.ngv

# timestamp resolution seems to be 100 ns:
# https://github.com/sansigormacros/ncnrsansigormacros/blob/ee3680d660331c0748343d24da931169b4984645/NCNR_User_Procedures/Reduction/VSANS/V_EventModeProcessing.ipf#L1231

TIMESTAMP_RESOLUTION = 100e-9

class vsans_events(object):
    header_dtype = np.dtype([ 
        ('magic_number', 'S5'),
        ('revision', 'u2'),
        ('data_offset', 'u2'),
        ('origin_timestamp', '10u1'),
        ('detector_carriage_group', 'S1'),
        ('HV_reading', 'u2'),
        ('timestamp_frequency', 'u4')
    ])

    data_dtype = np.dtype([
        ('tubeID', 'u1'),
        ('pixel',  'u1'),
        ('timestamp', '6u1')
    ])

    def __init__(self, filename):
        self.file = open(filename, 'rb')
        self.header = np.fromfile(self.file, dtype=self.header_dtype, count=1, offset=0)
        self.origin_timestamp = {
            "seconds": np.pad(self.header['origin_timestamp'][0][4:10], (0,2)).view(np.uint64)[0],
            "nanoseconds": self.header['origin_timestamp'][0][0:4].view(np.uint32)[0]
        }
        self.data_offset = self.header['data_offset'][0]
        header_size = self.header_dtype.itemsize
        num_disabled = self.data_offset - header_size # 1 byte per disabled tube.
        self.disabled_tubes = np.fromfile(self.file, count=num_disabled, offset=header_size, dtype='u1')
        self.read_data()
        self.process_timestamps()
    
    def seek_data_start(self):
        self.file.seek(self.data_offset)

    @property
    def simple_header(self):
        keys = self.header_dtype.names
        values = [self.header[k] for k in keys]
        values = [v[0] if len(v) == 1 else v for v in values]
        return dict(zip(keys, values))

    def read_data(self):
        self.seek_data_start()
        self.data = np.fromfile(self.file, dtype=self.data_dtype, count=-1)
        self.file.close()

    def process_timestamps(self):
        ts = self.data['timestamp']
        self.ts = np.pad(ts, ((0,0), (0, 2)), 'constant').view(np.uint64)[:,0]

    def rebin(self, time_slices=10):
        if hasattr(time_slices, 'size'):
            # then it's an array, treat as bin edges in seconds:
            time_slices = time_slices / TIMESTAMP_RESOLUTION
        time_edges = np.histogram_bin_edges(self.ts, bins=time_slices)
        #print(time_edges)
        time_bins = np.searchsorted(time_edges, self.ts, side='left')
        n_bins = len(time_edges) - 1
        #print(n_bins, time_slices, time_edges, time_bins)
        
        # include two extra bins for the timestamps that fall outside the defined bins
        # (those with indices 0 and n_bins + 1); for an array of size n+1 searchsorted
        # returns insertion indices from 0 (below the left edge) to n+1 (past the right edge)
        time_sliced_output = np.zeros((192, 128, n_bins + 2))
        # the operation below can be repeated... streaming histograms!
        np.add.at(time_sliced_output, (self.data['tubeID'], self.data['pixel'], time_bins), 1)
        # throw away the data in the outside bins
        time_sliced_output = time_sliced_output[:,:,1:-1]


        detectors = {
            "right": np.fliplr(time_sliced_output[0:48]),
            "left": np.flipud(time_sliced_output[144:192]),
            "top": (time_sliced_output[48:96]).swapaxes(0,1),
            "bottom": np.flipud(np.fliplr((time_sliced_output[96:144]).swapaxes(0,1)))
        }

        # returns: detectors data, and bin edges in seconds
        return detectors, time_edges * TIMESTAMP_RESOLUTION

    def counts_vs_time(self, start_time=0, timestep=1.0):
        """ get total counts on all detectors as a function of time,
        where the time bin size = timestep (in seconds) """
        max_timestamp = self.ts.max()
        start_timestamp = start_time / TIMESTAMP_RESOLUTION
        timestamp_step = timestep/TIMESTAMP_RESOLUTION
        bin_edges = np.arange(start_time, max_timestamp + timestamp_step, timestamp_step)
        hist, _ = np.histogram(self.ts, bins=bin_edges, range=(start_timestamp, max_timestamp))
        time_axis = (bin_edges[:-1] + timestamp_step/2.0) * TIMESTAMP_RESOLUTION
        return time_axis, hist


def demo():
    filename = "./sample_events/20191005231924501_1.hst"
    events = vsans_events(filename)

    detectors = events.rebin(10)
    #for det in detectors:
    #    print(det, 'sum:', np.sum(detectors[det]))
    
    return events

if __name__ == "__main__":
    demo()