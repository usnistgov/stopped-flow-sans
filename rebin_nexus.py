import h5py
import io
import numpy as np

from read_vsans_events_class import vsans_events
from get_eventfiles import retrieve_from_nexus

class Rebin(object):
    """ a class for holding a source nexus file, 
    retrieving the event files and processing them """
    def __init__(self, nexusfile):
        # nexusfile should be the path (string) to a nexus file
        self.nexusfile = nexusfile
        self.nexus = h5py.File(nexusfile, mode="r")
        self.front_eventfile, self.middle_eventfile = retrieve_from_nexus(nexusfile)
        self.front_events = vsans_events(self.front_eventfile)
        self.middle_events = vsans_events(self.middle_eventfile)

    def plot_counts_vs_time(self, timestep=1.0):
        import matplotlib.pyplot as plt
        t_middle, hist_middle = self.middle_events.counts_vs_time(timestep=timestep)
        t_front, hist_front = self.front_events.counts_vs_time(timestep=timestep)
        plt.plot(t_middle, hist_middle, label="middle")
        plt.plot(t_front, hist_front, label="front")
        plt.ylabel("counts")
        plt.xlabel("time (seconds)")
        plt.legend()
        plt.show()

    def rebin_selections(self, label="Exp", timestep=1.0):
        import matplotlib.pyplot as plt
        from matplotlib.widgets import SpanSelector, Button, TextBox

        # Fixing random state for reproducibility
        t_middle, hist_middle = self.middle_events.counts_vs_time(timestep=timestep)
        t_front, hist_front = self.front_events.counts_vs_time(timestep=timestep)
        
        fig, ax = plt.subplots()
        plt.subplots_adjust(bottom=0.2)
        plt.plot(t_middle, hist_middle, label="middle")
        plt.plot(t_front, hist_front, label="front")
        plt.ylabel("counts")
        plt.xlabel("time (seconds)")
        plt.legend()
        
        regions = []

        def onselect(xmin, xmax):
            ax.axvspan(xmin, xmax, alpha=0.5, color='red')
            regions.append([xmin, xmax])
            print([xmin, xmax])
            

        span = SpanSelector(ax, onselect, 'horizontal', useblit=True,
                            rectprops=dict(alpha=0.5, facecolor='blue'))
        # Set useblit=True on most backends for enhanced performance.

        axlabel = plt.axes([0.5, 0.05, 0.3, 0.075])
        axdone = plt.axes([0.81, 0.05, 0.1, 0.075])
        text_box = TextBox(axlabel, 'Label: ', initial=label)
        bdone = Button(axdone, 'Done')

        def ondone(event):
            ordered_regions = sorted(regions, key=lambda xrange: xrange[0])
            self._process_selections(ordered_regions, label=text_box.text)
            #print(regions)
            #print(text_box.text)
            plt.ioff()
            print('interactive mode off')
            plt.close(fig)
            print('figures closed')
            
        bdone.on_clicked(ondone)
        plt.show(block=True)
        print('done plotting')

    def _process_selections(self, regions, label=""):
        suffix = ".nxs.ngv"
        basename = self.nexusfile.replace(suffix, "")
        n = len(regions)
        detectors = {}
        for i, region in enumerate(regions):
            detectors["front"], bins_in_seconds = self.front_events.rebin(time_slices=np.array(region))
            detectors["middle"], bins_in_seconds = self.middle_events.rebin(time_slices=np.array(region))
            bin_width = region[1] - region[0]
            output = io.BytesIO(open(self.nexusfile, 'rb').read())
            h = h5py.File(output, mode='r+')
            entry = list(h.values())[0]
            original_count_time = entry['DAS_logs/counter/liveTime'][0]
            original_monitor = entry['DAS_logs/counter/liveMonitor'][0]
            entry['DAS_logs/counter/liveTime'][0] = bin_width
            entry['DAS_logs/counter/startTime'][0] = region[0]
            entry['DAS_logs/counter/stopTime'][0] = region[1]
            entry['collection_time'][0] = bin_width
            entry['DAS_logs/counter/liveMonitor'][0] = int(original_monitor * bin_width / original_count_time)
            for panel_group in ["front", "middle"]:
                group_key = panel_group[0].upper()
                panels = detectors[panel_group]
                for panel_name in panels:
                    # right, left, top, bottom
                    panel = panels[panel_name]
                    panel_key = panel_name[0].upper()
                    detector = entry['instrument/detector_%s%s' % (group_key,panel_key)]
                    #print(detector['data'].attrs['target'])
                    target = detector['data'].attrs['target']
                    detector['data'][...] = panel[:,:,0]
                    detector['integrated_count'][0] = panel[:,:,0].sum()
            h.close()
            output.seek(0)
            out_filename = "%s_%s_%d_of_%d%s" % (basename, label, i+1, n, suffix)
            print("writing: %s" % (out_filename))
            open(out_filename, 'wb').write(output.getbuffer())

    def do_rebinning(self, time_bins):
        if hasattr(time_bins, 'size'):
            # then it's a numpy array:
            n = len(time_bins) - 1
        else:
            n = time_bins
        suffix = ".nxs.ngv"
        basename = self.nexusfile.replace(suffix, "")
        detectors = {}
        detectors["front"], bins_in_seconds = self.front_events.rebin(time_slices=time_bins)
        detectors["middle"], bins_in_seconds = self.middle_events.rebin(time_slices=time_bins)
        bin_widths = np.diff(bins_in_seconds)
        for i in range(n):
            output = io.BytesIO(open(self.nexusfile, 'rb').read())
            h = h5py.File(output, mode='r+')
            entry = list(h.values())[0]
            original_count_time = entry['DAS_logs/counter/liveTime'][0]
            original_monitor = entry['DAS_logs/counter/liveMonitor'][0]
            entry['DAS_logs/counter/liveTime'][0] = bin_widths[i]
            entry['DAS_logs/counter/startTime'][0] = bins_in_seconds[i]
            entry['DAS_logs/counter/stopTime'][0] = bins_in_seconds[i+1]
            entry['collection_time'][0] = bin_widths[i]
            entry['DAS_logs/counter/liveMonitor'][0] = int(original_monitor * bin_widths[i] / original_count_time)
            for panel_group in ["front", "middle"]:
                group_key = panel_group[0].upper()
                panels = detectors[panel_group]
                for panel_name in panels:
                    # right, left, top, bottom
                    panel = panels[panel_name]
                    panel_key = panel_name[0].upper()
                    detector = entry['instrument/detector_%s%s' % (group_key,panel_key)]
                    #print(detector['data'].attrs['target'])
                    target = detector['data'].attrs['target']
                    #detector.data = panel[:,:,i]
                    detector['data'][...] = panel[:,:,i]
                    detector['integrated_count'][0] = panel[:,:,i].sum()
            h.close()
            output.seek(0)
            out_filename = "%s_%d_of_%d%s" % (basename, i+1, n, suffix)
            print("writing: %s" % (out_filename))
            open(out_filename, 'wb').write(output.getbuffer())

                    
