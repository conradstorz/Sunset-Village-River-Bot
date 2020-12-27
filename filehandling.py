#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Standardize methods for file handling. 
    The functions include verifing filenames are safe for OS in use.
    Files are handled using the pathlib approach.
    Data can be saved in flat CSV files from several types of data formats.
    Sub-Directory structures can be generated from timestamps.
    CSV files get appended if they already exist.
"""

from pathlib import Path


def clean_filename_str(fn):
    """Remove invalid characters from provided string."""
    return Path("".join(i for i in fn if i not in "\/:*?<>|"))


def check_and_validate(fname, direc, rename=False):
    """Return a PathObj for this filename/directory.
    Fail if filename already exists in directory but optionally rename.
    """
    fn = clean_filename_str(fname)
    direc.mkdir(parents=True, exist_ok=True)
    OUT_PATH_HANDLE = Path(direc, fn)
    """
    i = 0
    while Path(OUT_PATH_HANDLE).exists():
        if rename: # this routine does not currently work
            # TODO  strip old (#) from name and rename
            i += 1
            fn = f"{fn}({i})"
            OUT_PATH_HANDLE = Path(direc, fn)
        else:
            raise (FileExistsError)
    """
    return OUT_PATH_HANDLE


def create_timestamp_subdirectory_Structure(timestamp: str):
    """
    Takes a string (2020-10-05_020600UTC) representing a datetime
    and attempts to create a directory structure in the format ./YYYY/MM/DD/ 
    and returns a string representation of the directory.
    """
    date, time = timestamp.split("_")  # split date from time
    yy, mm, dd = date.split("-")
    _hh = time[:2]
    OP = f"{yy}/{mm}/{dd}/"
    return OP



# NOTES FOR USE OF pathlib

""" access parts of a filename:
>>> Path('static/dist/js/app.min.js').name
'app.min.js'
>>> pathobj = Path('static/dist/js/app.min.js')
>>> print(pathobj.name)
'app.min.js'
>>> Path('static/dist/js/app.min.js').suffix
'.js'
>>> Path('static/dist/js/app.min.js').suffixes
'.min.js'
>>> Path('static/dist/js/app.min.js').stem
'app'
"""

# set your reference point with the location of the python file you’re writing in
# this_file = Path(__file__)

# Here are three ways to get the folder of the current python file
# this_folder1 = Path(__file__, "..")
# this_folder2 = Path(__file__) / ".."
# this_folder3 = Path(__file__).parent

# This will fail:
# assert this_folder1 == this_folder2 == this_folder3
# becasue the variables are relative paths.

# The resolve() method removes '..' segments, follows symlinks, and returns
# the absolute path to the item.
# this works:
# assert this_folder1.resolve() == this_folder2.resolve() == this_folder3.resolve()


# folder_where_python_was_run = Path.cwd()

# create a new folder:
# Path("/my/directory").mkdir(parents=True, exist_ok=True)

# find path to your running code
# project_root = Path(__file__).resolve().parents[1] # this is the folder 2 levels up from your running code.

# create a new PathObj:
# static_files = project_root / 'static' # if you like this sort of thing they overrode the divide operator.
# media_files = Path(project_root, 'media') # I prefer this method.

# how to define 2 sub-directories at once:
# compiled_js_folder = static_files.joinpath('dist', 'js') # this is robust across all OS.

# gather items from specified path
# list(static_files.iterdir()) # returns a list of all items in directory.
# [x for x in static_files.iterdir if x.is_dir()] # list of only directories in a folder.
# [x for x in static_files.iterdir if x.is_file()] # same for files only.

# get a list of items matching a pattern:
# files = list(compiled_js_folder.glob('*.js')) # returns files ending with '.js'.

# sort the list of files by timestamp:
# files.sort(key=lambda fn: fn.stat().st_atime)
# atime, mtime, ctime don't seem to mean what I think. (Pathlib error?)

# search recursively down your folders path:
# sorted(project_root.rglob('*.js'))

# verify a path exists:
# Path('relative/path/to/nowhere').exists() # returns: False

# Example of directory deletion by pathlib
# pathobj = Path("demo/")
# pathobj.rmdir()

# Example of file deletion by pathlib
# pathobj = Path("demo/testfile.txt")
# pathobj.unlink()

