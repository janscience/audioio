from nose.tools import assert_true, assert_false, assert_equal, assert_raises
import os
import numpy as np
import audioio.audiowriter as aw
import audioio.riffmetadata as rm
import audioio.audiometadata as amd


def generate_data():
    duration=2.0
    samplerate = 44100.0
    channels = 2
    t = np.arange(0.0, duration, 1.0/samplerate)
    data = np.sin(2.0*np.pi*880.0*t) * t/duration
    data = data.reshape((-1, 1))
    for k in range(data.shape[1], channels):
        data = np.hstack((data, data[:,0].reshape((-1, 1))/k))
    return data, samplerate

    
def test_metadata():
    data, rate = generate_data()
    filename = 'test.wav'
    imd = dict(IENG='JB', ICRD='2024-01-24', RATE=9,
               Comment='this is test1')
    iimd = {rm.info_tags.get(k, k): str(v) for k, v in imd.items()}
    bmd = dict(Description='a recording',
               OriginationDate='2024:01:24', TimeReference=123456,
               Version=42, CodingHistory='Test1\nTest2')
    bbmd = {k: str(v).replace('\n', '.') for k, v in bmd.items()}
    xmd = dict(Project='Record all', Note='still testing',
               Sync_Point_List=dict(Sync_Point='1', Sync_Point_Comment='great'))
    omd = iimd.copy()
    omd['Production'] = bbmd

    # INFO:
    md = dict(INFO=imd)
    aw.write_audio(filename, data, rate, md)
    mdd = amd.metadata(filename, False)
    assert_true('INFO' in mdd, 'INFO section exists')
    assert_equal(iimd, mdd['INFO'], 'INFO section matches')

    with open(filename, 'rb') as sf:
        mdd = amd.metadata(sf, False)
    assert_true('INFO' in mdd, 'INFO section exists')
    assert_equal(iimd, mdd['INFO'], 'INFO section matches')

    # BEXT:
    md = dict(BEXT=bmd)
    aw.write_audio(filename, data, rate, md)
    mdd = amd.metadata(filename, False)
    assert_true('BEXT' in mdd, 'BEXT section exists')
    assert_equal(bmd, mdd['BEXT'], 'BEXT section matches')

    # IXML:
    md = dict(IXML=xmd)
    aw.write_audio(filename, data, rate, md)
    mdd = amd.metadata(filename, False)
    assert_true('IXML' in mdd, 'IXML section exists')
    assert_equal(xmd, mdd['IXML'], 'IXML section matches')

    # ODML:
    md = dict(Recording=omd, Production=bbmd, Notes=xmd)
    aw.write_audio(filename, data, rate, md)
    mdd = amd.metadata(filename, False)
    assert_equal(md, mdd, 'ODML sections match')
    
    md = dict(INFO=imd, BEXT=bmd, IXML=xmd,
              Recording=omd, Production=bmd, Notes=xmd)
    aw.write_audio(filename, data, rate, md)
    mdd = amd.metadata(filename, False)
    assert_true('INFO' in mdd, 'INFO section exists')
    assert_equal(iimd, mdd['INFO'], 'INFO section matches')
    assert_true('BEXT' in mdd, 'BEXT section exists')
    assert_equal(bmd, mdd['BEXT'], 'BEXT section matches')
    assert_true('IXML' in mdd, 'IXML section exists')
    assert_equal(xmd, mdd['IXML'], 'IXML section matches')
    assert_true('Recording' in mdd, 'Recording section exists')
    assert_true('Production' in mdd, 'Recording section exists')
    assert_true('Notes' in mdd, 'Recording section exists')
    assert_equal(md['Notes'], mdd['Notes'], 'Notes section matches')

    # INFO with nested dict:
    imd['SUBI'] = bmd
    md = dict(INFO=imd)
    aw.write_audio(filename, data, rate, md)

    # BEXT with invalid tag:
    bmd['xxx'] = 'no bext'
    md = dict(BEXT=bmd)
    aw.write_audio(filename, data, rate, md)
    
    amd.metadata(filename, True)
    os.remove(filename)


def test_flatten():
    md = dict(aaaa=2, bbbb=dict(ccc=3, ddd=4),
              eeee=dict(fff=5, ggg=dict(hh=6)),
              iiii=dict(jjj=7))

    fmd = amd.flatten_metadata(md, False)
    fmd = amd.flatten_metadata(md, True)
    amd.unflatten_metadata(fmd)

    amd.print_metadata(md)
    amd.print_metadata(md, '# ')
    amd.print_metadata(md, '# ', 2)
    filename = 'test.txt'
    amd.write_metadata_text(filename, md)
    os.remove(filename)

    
def test_markers():
    data, rate = generate_data()
    locs = np.random.randint(10, len(data)-10, (5, 2))
    locs = locs[np.argsort(locs[:,0]),:]
    locs[:,1] = np.random.randint(0, 20, len(locs))
    labels = np.zeros((len(locs), 2), dtype=np.object_)
    for i in range(len(labels)):
        labels[i,0] = chr(ord('a') + i % 26)
        labels[i,1] = chr(ord('A') + i % 26)*5
    filename = 'test.wav'
    
    aw.write_audio(filename, data, rate, None, locs)
    llocs, llabels = amd.markers(filename)
    assert_equal(len(llabels), 0, 'no labels')
    assert_true(np.all(locs == llocs), 'same locs')
    
    aw.write_audio(filename, data, rate, None, locs[:,0])
    llocs, llabels = amd.markers(filename)
    assert_equal(len(llabels), 0, 'no labels')
    assert_true(np.all(locs[:,0] == llocs[:,0]), 'same locs')
    
    aw.write_audio(filename, data, rate, None, locs, labels)
    llocs, llabels = amd.markers(filename)
    assert_true(np.all(locs == llocs), 'same locs')
    assert_true(np.all(labels == llabels), 'same labels')

    with open(filename, 'rb') as sf:
        llocs, llabels = amd.markers(sf)
    assert_true(np.all(locs == llocs), 'same locs')
    assert_true(np.all(labels == llabels), 'same labels')
    
    assert_raises(IndexError, aw.write_audio, filename, data, rate,
                  None, locs, labels[:-2,:])
    
    aw.write_audio(filename, data, rate, None, locs, labels[:,0])
    llocs, llabels = amd.markers(filename)
    assert_true(np.all(locs == llocs), 'same locs')
    assert_true(np.all(labels[:,0] == llabels[:,0]), 'same labels')
    
    aw.write_audio(filename, data, rate, None, locs[:,0], labels[:,0])
    llocs, llabels = amd.markers(filename)
    assert_true(np.all(locs[:,0] == llocs[:,0]), 'same locs')
    assert_true(np.all(labels[:,0] == llabels[:,0]), 'same labels')

    labels = np.zeros((len(locs), 2), dtype=np.object_)
    aw.write_audio(filename, data, rate, None, locs, labels)
    llocs, llabels = amd.markers(filename)
    assert_true(np.all(locs == llocs), 'same locs')
    assert_equal(len(llabels), 0, 'no labels')

    locs[:,-1] = 0
    aw.write_audio(filename, data, rate, None, locs)
    llocs, llabels = amd.markers(filename)
    assert_equal(len(llabels), 0, 'no labels')
    assert_true(np.all(locs == llocs), 'same locs')

    os.remove(filename)

    filename = 'test.xyz'
    with open(filename, 'wb') as df:
        df.write(b'XYZ!')
    mmd = amd.metadata(filename)
    llocs, llabels = amd.markers(filename)

    os.remove(filename)

    amd.print_markers(locs[:,0])
    amd.print_markers(locs)
    amd.print_markers(locs, labels[:,0])
    amd.print_markers(locs, labels)
    filename = 'test.txt'
    amd.write_markers(filename, locs, labels)
    os.remove(filename)

    
def test_main():
    data, rate = generate_data()
    filename = 'test.wav'
    md = dict(IENG='JB', ICRD='2024-01-24', RATE=9,
              Comment='this is test1')
    locs = np.random.randint(10, len(data)-10, (5, 2))
    locs = locs[np.argsort(locs[:,0]),:]
    locs[:,1] = np.random.randint(0, 20, len(locs))
    labels = np.zeros((len(locs), 2), dtype=np.object_)
    for i in range(len(labels)):
        labels[i,0] = chr(ord('a') + i % 26)
        labels[i,1] = chr(ord('A') + i % 26)*5
    aw.write_audio(filename, data, rate, md, locs, labels)
    assert_raises(SystemExit, amd.main)
    assert_raises(SystemExit, amd.main, '-h')
    assert_raises(SystemExit, amd.main, '--help')
    assert_raises(SystemExit, amd.main, '--version')
    amd.main('test.wav')
    amd.main('-m', 'test.wav')
    amd.main('-c', 'test.wav')
    amd.main('-m', '-c', 'test.wav')
    aw.write_audio(filename, data, rate, md, locs)
    amd.main('test.wav')
    os.remove('test.wav')


