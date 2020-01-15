# Licensed under a MIT style license - see LICENSE

"""MUSE-PHANGS core module
"""
# For print - see compatibility with Python 3
from __future__ import print_function

__authors__   = "Eric Emsellem"
__copyright__ = "(c) 2017-2019, ESO + CRAL"
__license__   = "MIT license"
__contact__   = " <eric.emsellem@eso.org>"

# This module has been initially inspired by pieces of python codes
# developed by Kyriakos and Martina from the GTO MUSE MAD team
# and further rewritten by Mark van den Brok. 
# Thanks to all three for this!
# Note that several python packages exist which would provide
# similar functionalities. 
#
# Eric Emsellem adapted a version from early 2017, provided by Mark
# and adapted it for the needs of the PHANGS project (PI Schinnerer)
# Completely rewritten structure and standards

# Importing modules
import numpy as np

# Standard modules
import os
from os.path import join as joinpath

import copy

# Pyfits from astropy
try :
    import astropy as apy
    from astropy.io import fits as pyfits
except ImportError :
    raise Exception("astropy is required for this module")

# ascii reading
try :
    from astropy.io import ascii
except ImportError :
    raise Exception("astropy.io.ascii is required for this module")

try :
    from astropy.table import Table, setdiff, vstack, TableMergeError
except ImportError :
    raise Exception("astropy.table.Table is required for this module")

import warnings
from astropy.utils.exceptions import AstropyWarning

import datetime
from datetime import datetime as dt

# Importing pymusepipe modules
from pymusepipe.init_musepipe import InitMuseParameters
from pymusepipe.recipes_pipe import PipeRecipes
from pymusepipe.prep_recipes_pipe import PipePrep
import pymusepipe.util_pipe as upipe
from pymusepipe.config_pipe import (
        suffix_rawfiles,suffix_prealign,suffix_checkalign,
        listexpo_files,dic_listObject,dic_listMaster,dic_listMasterObject,
        listexpo_types,dic_geo_astrowcs_table)

__version__ = '2.0.2 (25/09/2019)'
#       Cleaning and adding comments
#__version__ = '2.0.0 (19 June 2019)'
#       Included an astropy table
#__version__ = '0.2.0 (22 May 2018)'
#__version__ = '0.1.0 (03 April    2018)'
#__version__ = '0.0.2 (08 March    2018)'
#__version__ = '0.0.1 (21 November 2017)'

# esorex_rc = "/home/soft/ESO/MUSE/muse-kit-2.2-5/esorex-3.12.3/etc/esorex.rc"
   
#########################################################################
# Useful Classes for the Musepipe
#########################################################################
class MyDict(dict) :
    """Dictionary with extra attributes
    """
    def __init__(self) :
        dict.__init__(self)

class PipeObject(object) :
    """Class to store the tables
    """
    def __init__(self, info=None) :
        """Initialise the nearly empty class
        Add _info for a description if needed
        """
        self._info = info

def lower_rep(text) :
    return text.replace("_","").lower()

#########################################################################
# Main class
#                           MusePipe
#########################################################################
class MusePipe(PipePrep, PipeRecipes):
    """Main Class to define and run the MUSE pipeline, given a certain galaxy name
    This is the main class used throughout the running of the pipeline
    which contains functions and attributes all associated with the reduction
    of MUSE exposures.
    """

    def __init__(self, targetname=None, pointing=0, folder_config="Config/",
            rc_filename=None, cal_filename=None, log_filename="MusePipe.log", 
            reset_log=False, verbose=True, musemode="WFM-NOAO-N", checkmode=True, 
            strong_checkmode=False, **kwargs):
        """Initialise the file parameters to be used during the run
        Create the python structure which allows the pipeline to run 
        either individual recipes or global ones

        Parameters
        ----------
        targetname: str [None]
            Name of the target (e.g., 'NGC1208').
        pointing: int [0]
            Number of the pointing to consider
        folder_config: str
            Folder name for the configuration files
        rc_filename: str
            Name of the input configuration file with the root folders
        cal_filename: str
            Name of the input configuration file with calibration file names
        log_filename: str ['MusePipe.log']
            Name of the log file where all pymusepipe output will be recorded
        reset_log: bool [False]
            If True, log file will be reset to an empty file before starting
        verbose: bool [True]
            Give more information as output
        musemode: str ['WFM-NOAO-N'] 
            String to define the mode to be considered
        checkmode: bool [True]
            Check the mode when reducing
        strong_checkmode: bool [True]
            Enforce the checkmode for all if True, 
            or exclude DARK/BIAS from check if False
        vsystemic: float [0.0]
            Systemic velocity of the galaxy [in km/s]

        Other possible entries
        ----------------------
        overwrite_astropy_table: bool [False]
            Overwrite the astropy table even when it exists.
        warnings: str ['ignore']
            If set to 'ignore', will ignore the Astropy Warnings.
        time_astrometry: bool [True]
            Use the time dependent geo_table and astrometry_wcs files
            following on the date of the input exposures (MJD)
        """
        # Verbose option
        self.verbose = verbose
        self._debug = kwargs.pop("debug", False)

        self._suffix_prealign = kwargs.pop("suffix_prealign", suffix_prealign)
        self._suffix_checkalign = kwargs.pop("suffix_checkalign", suffix_checkalign)

        # Warnings for astropy
        self.warnings = kwargs.pop("warnings", 'ignore')
        if self.warnings == 'ignore':
           warnings.simplefilter('ignore', category=AstropyWarning)

        # Overwriting option for the astropy table
        self._overwrite_astropy_table = kwargs.pop("overwrite_astropy_table", False)
        # Updating the astropy table
        self._update_astropy_table = kwargs.pop("update_astropy_table", False)

        # Use time dependent geo_table
        self._time_astrometry = kwargs.pop("time_astrometry", True)

        # Set alignment saving option
        self._save_alignment_images = kwargs.pop("save_alignment_images", True)

#        super(MusePipe, self).__init__(**kwargs)
        # Filter for alignment
        self.filter_for_alignment = kwargs.pop("filter_for_alignment", "Cousins_R")
        self.filter_list = kwargs.pop("filter_list", "white")

        # Setting the default attibutes #####################
        self.targetname = targetname
        self.pointing = pointing
        self.vsystemic = np.float(kwargs.pop("vsystemic", 0.))

        # Setting other default attributes
        if log_filename is None : 
            log_filename = "log_{timestamp}.txt".format(timestamp=upipe.create_time_name())
            upipe.print_info("The Log file will be {log}".format(log=log_filename), pipe=self)
        self.log_filename = log_filename

        # Further reduction options =====================================
        # Mode of the observations
        self.musemode = musemode
        # Checking if mode is correct
        self.checkmode = checkmode
        # Checking if mode is correct also for BIAS & DARK
        self.strong_checkmode = strong_checkmode
        # End of parameter settings #########################

        # Extra parameters for the initialisation and starting of recipes
        first_recipe = kwargs.pop("first_recipe", 1)
        last_recipe = kwargs.pop("last_recipe", None)
        init_raw_table = kwargs.pop("init_raw_table", True)

        # Init of the subclasses
        PipePrep.__init__(self, first_recipe=first_recipe, last_recipe=last_recipe)
        PipeRecipes.__init__(self, **kwargs)

        # =========================================================== #
        # Setting up the folders and names for the data reduction
        # Can be initialised by either an rc_file, 
        # or a default rc_file or harcoded defaults.
        self.pipe_params = InitMuseParameters(folder_config=folder_config,
                            rc_filename=rc_filename, 
                            cal_filename=cal_filename, verbose=verbose)

        # Setting up the relative path for the data, using Galaxy Name + Pointing
        self.pipe_params.data = "{0}/P{1:02d}/".format(self.targetname, self.pointing)

        # Create full path folder 
        self.set_fullpath_names()
        self.paths.log_filename = joinpath(self.paths.log, log_filename)

        # Go to the data directory
        # and Recording the folder where we start
        self.paths.orig = os.getcwd()

        # Making the output folders in a safe mode
        upipe.print_info("Creating directory structure", pipe=self)
        self.goto_folder(self.paths.data)

        # ==============================================
        # Creating the extra pipeline folder structure
        for folder in self.pipe_params._dic_input_folders.keys() :
            upipe.safely_create_folder(self.pipe_params._dic_input_folders[folder], verbose=verbose)

        # ==============================================
        # Creating the folder structure itself if needed
        for folder in self.pipe_params._dic_folders.keys() :
            upipe.safely_create_folder(self.pipe_params._dic_folders[folder], verbose=verbose)

        # ==============================================
        # Init the Master exposure flag dictionary
        self.Master = {}
        for mastertype in dic_listMaster.keys() :
            upipe.safely_create_folder(self._get_path_expo(mastertype, "master"), verbose=verbose)
            self.Master[mastertype] = False

        # Init the Object folder
        for objecttype in dic_listObject.keys() :
            upipe.safely_create_folder(self._get_path_expo(objecttype, "processed"), verbose=verbose)

        self._dic_listMasterObject = dic_listMasterObject

        # ==============================================
        # Creating the folders in the TARGET root folder 
        # e.g, for the alignment images
        for name in list(self.pipe_params._dic_folders_target.keys()):
            upipe.safely_create_folder(getattr(self.paths, name), verbose=verbose)

        # ==============================================
        # Going back to initial working directory
        self.goto_origfolder()

        # ===========================================================
        # Transform input dictionary of geo/astro files for later
        # This is useful for the creation of the sof files
        self._init_geoastro_dates()

        if init_raw_table:
            self.init_raw_table()
            self._raw_table_initialised = True
        else:
            self._raw_table_initialised = False
        self.read_all_astro_tables()

    def _add_targetname(self, name):
        """Add targetname to input name and return it
        
        Input
        -----
        name: str

        Returns
        -------
        new name including targetname
        """
        if if self.add_targetname:
            return "{0}_{1}".format(self.targetname, name)
        else:
            return name

    def _init_geoastro_dates(self):
        """Initialise the dictionary for the geo and astrometry files
        Transforms the dates into datetimes
        """
        self._dic_geoastro = {}
        for name in dic_geo_astrowcs_table:
            startd = dt.strptime(dic_geo_astrowcs_table[name][0], 
                                 "%Y-%m-%d").date()
            endd = dt.strptime(dic_geo_astrowcs_table[name][1], 
                               "%Y-%m-%d").date()
            self._dic_geoastro[name] = [startd, endd]

    def retrieve_geoastro_name(self, date_str, filetype='geo', mode='wfm'):
        """Retrieving the astrometry or geometry fits file name

        Parameters
        ----------
        date_str: str
            Date as a string (DD/MM/YYYY)
        filetype: str
            'geo' or 'astro', type of the needed file
        mode: str
            'wfm' or 'nfm' - MUSE mode
        """
        dic_pre = {'geo': 'geometry_table', 
                      'astro': 'astrometry_wcs'}
        if filetype not in dic_pre.keys():
            upipe.print_error("Could not decipher the filetype option "
                              "in retrieve_geoastro")
            return None
    
        # Transform into a datetime date
        date_dt = dt.strptime(date_str, "%Y-%m-%dT%H:%M:%S").date()
        # get all the distance to the dates (start+end together)
        near = {min(abs(date_dt - self._dic_geoastro[name][0]), 
                         abs(date_dt - self._dic_geoastro[name][1])) : 
                         name for name in self._dic_geoastro}
        # Find the minimum distance and get the name
        ga_suffix = near[min(near.keys())]
        # Build the name with the prefix, suffix and mode
        ga_name = "{0}_{1}_{2}.fits".format(dic_pre[filetype],
                                            mode, ga_suffix)
        return ga_name

    def _set_option_astropy_table(self, overwrite=None, update=None):
        """Set the options for overwriting or updating the astropy tables
        """
        if overwrite is not None: self._overwrite_astropy_table = overwrite
        if update is not None: self._update_astropy_table = update

    def goto_origfolder(self, addtolog=False) :
        """Go back to original folder
        """
        upipe.print_info("Going back to the original folder {0}".format(
                             self.paths.orig), pipe=self)
        self.goto_folder(self.paths.orig, addtolog=addtolog, verbose=False)
            
    def goto_prevfolder(self, addtolog=False) :
        """Go back to previous folder

        Parameters
        ----------
        addtolog: bool [False]
            Adding the folder move to the log file
        """
        upipe.print_info("Going back to the previous folder {0}".format(
                             self.paths._prev_folder), pipe=self)
        self.goto_folder(self.paths._prev_folder, addtolog=addtolog, verbose=False)
            
    def goto_folder(self, newpath, addtolog=False, **kwargs) :
        """Changing directory and keeping memory of the old working one

        Parameters
        ----------
        addtolog: bool [False]
            Adding the folder move to the log file
        """
        verbose = kwargs.pop("verbose", self.verbose)
        try: 
            prev_folder = os.getcwd()
            newpath = os.path.normpath(newpath)
            os.chdir(newpath)
            upipe.print_info("Going to folder {0}".format(newpath), pipe=self)
            if addtolog :
                upipe.append_file(self.paths.log_filename, "cd {0}\n".format(newpath))
            self.paths._prev_folder = prev_folder 
        except OSError:
            if not os.path.isdir(newpath):
                raise
    
    def set_fullpath_names(self) :
        """Create full path names to be used
        """
        # initialisation of the full paths 
        self.paths = PipeObject("All Paths useful for the pipeline")
        self.paths.root = self.pipe_params.root
        self.paths.data = joinpath(self.paths.root, self.pipe_params.data)
        self.paths.target = joinpath(self.paths.root, self.targetname)

        for name in list(self.pipe_params._dic_folders.keys()) + list(self.pipe_params._dic_input_folders.keys()):
            setattr(self.paths, name, joinpath(self.paths.data, getattr(self.pipe_params, name)))

        # Creating the filenames for Master files
        self.paths.Master = PipeObject("All Paths for Master files useful for the pipeline")
        for expotype in dic_listMaster.keys() :
            # Adding the path of the folder
            setattr(self.paths.Master, self._get_attr_expo(expotype), 
                    joinpath(self.paths.data, self._get_path_expo(expotype, "master")))

        self._dic_paths = {"master": self.paths.Master, "processed": self.paths}

        # Creating the attributes for the folders needed in the TARGET root folder, e.g., for alignments
        for name in list(self.pipe_params._dic_folders_target.keys()):
            setattr(self.paths, name, joinpath(self.paths.target, self.pipe_params._dic_folders_target[name]))

    def _reset_tables(self) :
        """Reseting the astropy Tables for expotypes
        """
        # Reseting the select_type item
        self.Tables = PipeObject("Astropy Tables")
        # Creating the other two Tables categories
        self.Tables.Raw = PipeObject("Astropy Tables for each raw expotype")
        self.Tables.Master = PipeObject("Astropy Tables for each mastertype")
        self.Tables.Processed = PipeObject("Astropy Tables for each processed type")
        self.Tables.Reduced = PipeObject("Astropy Tables for each reduced type")
        self._dic_tables = {"raw": self.Tables.Raw, "master": self.Tables.Master,
                "processed": self.Tables.Processed, "reduced": self.Tables.Reduced}
        self._dic_suffix_astro = {"raw": "RAW", "master": "MASTER", 
                "processed": "PRO", "reduced": "RED"}

        for expotype in listexpo_types.keys() :
            setattr(self.Tables.Raw, self._get_attr_expo(expotype), [])

    def read_all_astro_tables(self, reset=False) :
        """Initialise all existing Astropy Tables
        """
        if reset or not hasattr(self, "Tables"):
            self._reset_tables()

        for mastertype in dic_listMaster.keys():
            setattr(self._dic_tables["master"], self._get_attr_expo(mastertype),
                self.read_astropy_table(mastertype, stage="master"))

        for expotype in dic_listObject.keys():
            setattr(self._dic_tables["processed"], self._get_attr_expo(expotype),
                self.read_astropy_table(expotype, stage="processed"))

    def read_astropy_table(self, expotype=None, stage="master"):
        """Read an existing Masterfile data table to start the pipeline
        """
        # Read the astropy table
        name_table = self._get_fitstablename_expo(expotype, stage)
        if not os.path.isfile(name_table):
            upipe.print_warning("Astropy table {0} does not exist - setting up an "
                                " empty one".format(name_table), pipe=self)
            return Table([[],[],[]], names=['tpls','mjd', 'tplnexp'])
        else :
            upipe.print_info("Reading Astropy fits Table {0}".format(name_table),
                                 pipe=self)
            return Table.read(name_table, format="fits")
        
    def init_raw_table(self, reset=False, **kwargs):
        """ Create a fits table with all the information from
        the Raw files. Also create an astropy table with the same info

        Parameters
        ----------
        reset: bool [False]
            Resetting the raw astropy table if True
        """
        upipe.print_info("Creating the astropy fits raw data table", pipe=self)

        if reset or not hasattr(self, "Tables"):
            self._reset_tables()

        # Testing if raw table exists
        name_table = self._get_fitstablename_expo('RAWFILES', "raw")

        # ---- File exists - we READ it ------------------- #
        overwrite = kwargs.pop("overwrite", self._overwrite_astropy_table)
        if os.path.isfile(name_table) :
            if overwrite:
                upipe.print_warning("The raw-files table will be overwritten", 
                        pipe=self)
            else :
                upipe.print_warning("The raw files table already exists", 
                        pipe=self)
                upipe.print_warning("If you wish to overwrite it, "
                      " please turn on the 'overwrite_astropy_table' option to 'True'", 
                      pipe=self)
                upipe.print_warning("In the meantime, the existing table will be read and used", 
                        pipe=self)
                self.Tables.Rawfiles = self.read_astropy_table('RAWFILES', "raw")

        # ---- File does not exist - we create it ---------- #
        if overwrite:
            # Check the raw folder
            self.goto_folder(self.paths.rawfiles)
            # Get the list of files from the Raw data folder
            files = os.listdir(".")

            smalldic = {"FILENAME" : ['filename', '', str, '100A']}
            fulldic = listexpo_files.copy()
            fulldic.update(smalldic)

            # Init the lists
            MUSE_infodic = {}
            for key in fulldic.keys() :
                MUSE_infodic[key] = []

            # Looping over the files
            for f in files:
                # Excluding the files without MUSE and fits.fz
                if ('MUSE' in f):
                    if any([f.endswith(suffix) for suffix in suffix_rawfiles]):
                        MUSE_infodic['FILENAME'].append(f)
                        header = pyfits.getheader(f, 0)
                        for k in listexpo_files.keys() :
                            [namecol, keyword, func, form] = listexpo_files[k]
                            MUSE_infodic[k].append(func(header[keyword]))
                    elif any([suffix in f for suffix in suffix_rawfiles]):
                        upipe.print_warning("File {0} will be ignored "
                                            "from the Raw files "
                                            "(it may be a download duplicate - "
                                            " please check)".format(f),
                                            pipe=self)

            # Transforming into numpy arrayimport pymusepipe
            for k in fulldic.keys() :
                MUSE_infodic[k] = np.array(MUSE_infodic[k])

            # Getting a sorted array with indices
            idxsort = np.argsort(MUSE_infodic['FILENAME'])

            # Creating the astropy table
            self.Tables.Rawfiles = Table([MUSE_infodic['FILENAME'][idxsort]], 
                    names=['filename'], meta={'name': 'raw file table'})

            # Creating the columns
            for k in fulldic.keys() :
                [namecol, keyword, func, form] = fulldic[k]
                self.Tables.Rawfiles[namecol] = MUSE_infodic[k][idxsort]

            # Writing up the table
            self.Tables.Rawfiles.write(name_table, format="fits", 
                    overwrite=overwrite)

            if len(self.Tables.Rawfiles) == 0:
                upipe.print_warning("Raw Files Table is empty: please check your 'Raw' folder")

            # Going back to the original folder
            self.goto_prevfolder()

        # Sorting the types ====================================
        self.sort_raw_tables()

    def save_expo_table(self, expotype, tpl_gtable, stage="master", 
            fits_tablename=None, aggregate=True, suffix="", overwrite=None, update=None):
        """Save the Expo (Master or not) Table corresponding to the expotype
        """
        self._set_option_astropy_table(overwrite, update)

        if fits_tablename is None :
            fits_tablename = self._get_fitstablename_expo(expotype, stage, suffix)

        attr_expo = self._get_attr_expo(expotype)
        full_tablename = joinpath(self.paths.astro_tables, fits_tablename)

        if aggregate:
            table_to_save = tpl_gtable.groups.aggregate(np.mean)['tpls', 'mjd', 'tplnexp']
        else :
            table_to_save = copy.copy(tpl_gtable)

        # If the file already exists
        if os.path.isfile(full_tablename):
            # Check if we update
            if self._update_astropy_table:
                # Reading the existing table
                upipe.print_warning("Reading the existing Astropy table {0} "
                                    "in folder {1}".format(fits_tablename, 
                                    self.paths.astro_tables), pipe=self)
                existing_table = Table.read(full_tablename, format="fits")
                # first try to see if they are compatible by using vstack
                try: 
                    stack_temptable = vstack([existing_table, table_to_save], join_type='exact')
                    upipe.print_warning("Updating the existing Astropy table {0}".format(fits_tablename), 
                            pipe=self)
                    table_to_save = apy.table.unique(stack_temptable, keep='first')
                except TableMergeError:
                    upipe.print_warning("Astropy Table cannot be joined to the existing one", 
                            pipe=self)
                    return

            # Check if we want to overwrite or add the line in
            elif not self._overwrite_astropy_table:
                upipe.print_warning("Astropy Table {0} already exists, "
                    " use overwrite_astropy_table to overwrite it".format(fits_tablename), 
                    pipe=self)
                return

        table_to_save.write(full_tablename, format="fits", overwrite=True)
        setattr(self._dic_tables[stage], attr_expo, table_to_save)

    def sort_raw_tables(self, checkmode=None, strong_checkmode=None) :
        """Provide lists of exposures with types defined in the dictionary
        """
        if checkmode is not None : self.checkmode = checkmode
        else : checkmode = self.checkmode

        if strong_checkmode is not None : self.strong_checkmode = strong_checkmode
        else : strong_checkmode = self.strong_checkmode

        if len(self.Tables.Rawfiles) == 0:
            upipe.print_error("Raw files is empty, hence cannot be sorted")
            return

        # Sorting alphabetically (thus by date)
        for expotype in listexpo_types.keys() :
            try :
                mask = (self.Tables.Rawfiles['type'] == listexpo_types[expotype])
                if self.checkmode: 
                    maskmode = (self.Tables.Rawfiles['mode'] == self.musemode)
                    if (expotype.upper() not in exclude_list_checkmode) or self.strong_checkmode:
                        mask = maskmode & mask
                setattr(self.Tables.Raw, self._get_attr_expo(expotype), 
                        self.Tables.Rawfiles[mask])
            except AttributeError:
                pass

    def _get_attr_expo(self, expotype):
        return expotype.lower()

    def _get_fitstablename_expo(self, expotype, stage="master", suffix=""):
        """Get the name of the fits table covering
        a certain expotype
        """
        fitstablename = "{0}_{1}_{2}list_table.fits".format(self._dic_suffix_astro[stage], 
                expotype.lower(), suffix)
        return joinpath(self.paths.astro_tables, fitstablename)

    def _get_table_expo(self, expotype, stage="master"):
        try:
            return getattr(self._dic_tables[stage], self._get_attr_expo(expotype))
        except AttributeError:
            upipe.print_error("No attributed table with expotype {0} and stage {1}".format(expotype, stage))
            return Table()

    def _read_offset_table(self, offset_table_name=None, folder_offset_table=None):
        """Reading the Offset Table

        Input
        -----
        offset_table_name: str
            Name of the offset table
            Default is None
        folder_offset_table: str
            Name of the folder to find the offset table
            Default is None
        """
        self.offset_table_name = offset_table_name
        if self.offset_table_name is None:
            upipe.print_warning("No Offset table name given")
            self.offset_table = Table()
            return
        
        # Using the given folder name, alignment one by default
        if folder_offset_table is None:
            self.folder_offset_table = self.paths.alignment
        else:
            self.folder_offset_table = folder_offset_table

        full_offset_table_name = joinpath(self.folder_offset_table,
                                    self.offset_table_name)
        if not os.path.isfile(full_offset_table_name):
            upipe.print_error("Offset table [{0}] not found".format(
                full_offset_table_name))
            self.offset_table = Table()
            return

        # Opening the offset table
        self.offset_table = Table.read(full_offset_table_name)

    def _select_closest_mjd(self, mjdin, group_table) :
        """Get the closest frame within the expotype
        If the attribute does not exist in Tables, it tries to read
        the table from the folder
        """
        # Get the closest tpl
        index = np.argmin((mjdin - group_table['mjd'])**2)
        closest_tpl = group_table[index]['tpls']
        return index, closest_tpl

    def _get_path_expo(self, expotype, stage="master"):
        masterfolder = upipe.lower_allbutfirst_letter(expotype)
        if stage.lower() == "master":
            masterfolder = joinpath(self.pipe_params.master, masterfolder)
        return masterfolder

    def _get_fullpath_expo(self, expotype, stage="master"):
        return upipe.normpath(getattr(self._dic_paths[stage], self._get_attr_expo(expotype)))

    def _get_path_files(self, expotype) :
        return upipe.normpath(getattr(self.paths, expotype.lower()))
