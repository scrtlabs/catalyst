import bcolz

tmp_bundle = '/Users/adityapalepu/.catalyst/data/marketplace/temp_bundles/test_mktcap_adi-daily-2014'
bundle_folder = '/Users/adityapalepu/.catalyst/data/marketplace/test_mktcap_adi'

zsource = bcolz.ctable(rootdir=tmp_bundle, mode='r')
ztarget = bcolz.ctable(rootdir=bundle_folder, mode='a')

ztarget.append(zsource)
print(zsource.shape, ztarget.shape)