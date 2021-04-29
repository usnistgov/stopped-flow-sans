ENDPOINT = "http://nicedata.ncnr.nist.gov/eventfiles"
EVENTS_FOLDER = "eventfiles"

def filenames_from_nexus(nexusfile): #, events_folder=EVENTS_FOLDER):
    import h5py
    nexus = h5py.File(nexusfile, mode="r")
    entry = list(nexus.values())[0]
    front_eventfile = entry['instrument/detector_FR/event_file_name'][0].decode()
    middle_eventfile = entry['instrument/detector_MR/event_file_name'][0].decode()
    return front_eventfile, middle_eventfile

def retrieve(eventfile, events_folder=EVENTS_FOLDER, overwrite=False):
    import requests
    import os
    if not os.path.exists(events_folder):
        os.makedirs(events_folder)
    fullpath = os.path.join(events_folder, eventfile)
    if overwrite or not os.path.exists(fullpath):
        print('retrieving eventfile %s from %s' % (eventfile, ENDPOINT))
        r = requests.get(ENDPOINT, params={"instrument": "vsans", "filename": eventfile})
        if r.ok:
            open(fullpath, 'wb').write(r.content)
            print('success')
        else:
            print("failure: %d '%s'" % (r.status_code, r.reason))
    
def retrieve_from_nexus(nexusfile, events_folder=EVENTS_FOLDER, overwrite=False):
    import os
    front_eventfile, middle_eventfile = filenames_from_nexus(nexusfile)
    retrieve(front_eventfile, events_folder=events_folder, overwrite=overwrite)
    retrieve(middle_eventfile, events_folder=events_folder, overwrite=overwrite)

    return os.path.join(events_folder, front_eventfile), os.path.join(events_folder, middle_eventfile)


if __name__ == '__main__':
    retrieve_from_nexus("nexus_files/sans69040.nxs.ngv")
    