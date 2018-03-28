# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""MUSE-PHANGS initialisation of folders
"""

__authors__   = "Eric Emsellem"
__copyright__ = "(c) 2017, ESO + CRAL"
__license__   = "3-clause BSD License"
__contact__   = " <eric.emsellem@eso.org>"

# Importing modules
import warnings

# Standard modules
import os
from os.path import join as joinpath
import copy

############################################################
#                      BEGIN
# The following parameters can be adjusted for the need of
# the specific pipeline to be used
############################################################
# FOLDER structure, defined here
dic_namefolders = {
        "ReducedFiles": "ReducedFiles/", 
        "RawData": "RawData/",
        "SetOfFiles": "SOF/"}

# Default hard-coded folders
dic_folders = {
            # Muse calibration files (common to all)
            "musecalib_folder": "/soft/ESO/MUSE/muse-kit-2.2-5/muse-calib-2.2/cal/",
            # Calibration files (specific to OBs)
            "root_folder" : "/science/PHANGS/",
            # Raw Data files
            "rawdata_folder" : "Raw/",
            # Master Calibration files
            "mastercalib_folder" : "Master/",
            # Reduced files
            "reducedfiles_folder" : "Reduced/",
            # Sky Flat files
            "sky_folder" : "Sky/",
            # Cubes
            "cubes_folder" : "Cubes/",
            # Reconstructed Maps
            "maps_folder" : "Maps/",
            # Flag 
            "init_rcfile" : "Hardcoded Default - see init_musepipe.py module"
            }

# Default initialisation file
default_rc_filename = "~/.musepiperc"

# Default hard-coded fits files - Calibration Tables
# This should be replaced by an ascii file reading at some point
dic_calib_tables = {
            # Muse calibration files (common to all)
            "geo_table": "geometry_table_wfm.fits",
            # Calibration files (specific to OBs)
            "astro_table" : "astrometry_wcs_wfm.fits",
            # Raw Data files
            "badpix_table" : "badpix_table_2015-06-02.fits",
            # Reduced files
            "vignetting_table" : "vignetting_mask.fits",
            # Pixel tables
            "std_flux_Table" : "std_flux_table.fits",
            # Sky Flat files
            "extinct_table" : "extinct_table.fits",
            # Flag 
            "init_calfile" : "Hardcoded Default - see init_musepipe.py module"
            }

# ----------------- Galaxies and Pointings ----------------#

# Sample of galaxies
# For each galaxy, we provide the pointings numbers and the run attached to that pointing
MUSEPIPE_sample = {
        "NGC628": {1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0, 8:0, 9:0, 10:0, 11:0, 12:0},
        "NGC1087": {1:1}, 
        "NGC1672": {1:1, 2:1, 3:1, 4:1, 5:1}
        }

# List of MUSEPIPE Observing runs
# For each Observing run, we provide the start and end dates
MUSEPIPE_runs = {
        'Run00' : ['P099','2017-10-01','2017-10-31'],
        'Run01' : ['P100','2017-10-01','2017-10-31'], 
        'Run02' : ['P101','2017-11-01','2017-11-30']
        }

############################################################
#                      END
############################################################
class init_muse_parameters(object) :
    def __init__(self, dirname="", rc_filename=None, cal_filename=None, **kwargs) :
        """Define the default parameters (folders/calibration files) 
        and name suffixes for the MUSE data reduction
        """
        # Will first test if there is an rc_file provided
        # If not, it will look for a default rc_filename, the name of which is provided
        # above. If not, the hardcoded default will be used.
        if rc_filename is None :
            if not os.path.isfile(default_rc_filename):
                warnings.warn(("WARNING: No filename or {default_rc} file "
                     "to initialise from. We will use the default hardcoded " 
                     "in the init_musepipe.py module").format(default_rc=default_rc_filename), RuntimeWarning)
                self.init_default_param(dic_folders)

            else :
                self.read_param_file(default_rc_filename, dic_folders) 
        else :
            self.read_param_file(joinpath(dirname, rc_filename), dic_folders)

        # Same happens with the calibration files.
        # If filename is provided, will use that, otherwise use the hard coded values.
        if cal_filename is None :
            self.init_default_param(dic_calib_tables, self.musecalib_folder)
        else :
            self.read_param_file(joinpath(dirname, cal_filename), dic_calib_tables)

    def init_default_param(self, dic_param, input_suffix="") :
        """Initialise the parameters as defined in the input dictionary
        Hardcoded in init_musepipe.py
        """
        for key in dic_param.keys() :
            setattr(self, key, input_suffix + dic_param[key])

    def read_param_file(self, filename, dic_param) :
        """Reading an input parameter initialisation file 
        """

        # Testing existence of filename
        if not os.path.isfile(filename) :
            warnings.warn(("ERROR: input parameter {inputname} cannot be found. "
                    "We will use the default hardcoded in the "
                    "init_musepipe.py module").format(inputname=filename),
                    RuntimeWarning)
            return

        # If it exists, open and read it
        self.init_rcfile = filename
        f_param = open(filename)
        lines = f_param.readlines()

        # Dummy dictionary to see which items are not initialised
        dummy_dic_param = copy.copy(dic_param)
        for line in lines :
            if line[0] in ["#", "%"] : continue 

            sline = line.split()
            if sline[0] in dic_param.keys() :
                if sline[1][:] != "/" :
                    sline[1] += "/"

                setattr(self, sline[0], sline[1]) 
                # Here we drop the item which was initialised
                val = dummy_dic_param.pop(sline[0])
            else :
                continue

        # Set of non initialised folders
        not_initialised_param = dummy_dic_param.keys()
        # Listing them as warning and using the hardcoded default
        for key in not_initialised_param :
            warnings.warn(("WARNING: parameter {param} not initialised "
                   "We will use the default hardcoded value from "
                   "init_musepipe.py").format(param=key))
            setattr(self, key, dic_param[key])


####################################################
# Defining classes to get samples and objects
####################################################
class musepipe_sample(object) :
    def __init__(self) :
        self.sample = MUSEPIPE_sample
        self.targets = MUSEPIPE_sample.keys()

class musepipe_target(object) :
    def __init__(self, galaxyname=None, pointing=1) :
        if galaxyname not in MUSEPIPE_sample.keys() :
            print("ERROR: no Galaxy named {gal} in the defined sample".format(gal=galaxyname))
            return

        print("Initialising Target {name}".format(name=galaxyname))
        self.targetname = galaxyname
        self.info_pointings = MUSEPIPE_sample[galaxyname]
        if pointing not in self.info_pointings.keys() :
            print("ERROR: no pointing {pointing} for the Galaxy".format(pointing))
            return
        self.pointing = pointing
        self.run = self.info_pointings[pointing]
