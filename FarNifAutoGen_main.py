import sys
import os.path
import multiprocessing
import subprocess
import time
import glob
import shutil

from os import listdir, makedirs
from os.path import isfile, join

import FarNifAutoGen_processNif
#from FarNifAutoGen_processNif import processNif
#from FarNifAutoGen_processNif import output_filename_path

# custom settings
os.environ["BLENDEREXE"] = "C:/Blender/blender.exe"
os.environ["FARNIFAUTOGEN_INPUT_DATADIR"] = "C:/Games/bsacmd/out/"

# set up user-defined settings

# set up executable path variables
if (os.environ.get("BLENDEREXE") is not None):
    blenderPath = os.environ["BLENDEREXE"]
else:
    blenderPath = "C:/Program Files (x86)/Blender Foundation/Blender/blender.exe"
if os.path.exists(blenderPath) == False:
    print "==================="
    print "ERROR: Blender was not found. Please set the BLENDEREXE variable to the path of your blender executable."
    print "==================="
    raw_input("Press ENTER to quit.")
    quit(-1)
if (os.environ.get("GIMPEXE") is not None):
    gimpPath = os.environ["GIMPEXE"]
else:
    gimpPath = "C:/Program Files/GIMP 2/bin/gimp-console-2.8.exe"
if os.path.exists(gimpPath) == False:
    print "==================="
    print "ERROR: GIMP was not found. Please set the GIMPEXE variable to the path of your blender executable."
    print "==================="
    raw_input("Press ENTER to quit.")
    quit(-1)

# global variables
nif_list_jobfile = "nif_list.job"
dds_list_jobfile = "lowres_list.job"
nif_joblist = dict()
dds_joblist = list()
# set up input/output path variables
#input_root = "./"
#input_path = input_root + ""
if (os.environ.get("FARNIFAUTOGEN_INPUT_DATADIR") is not None):
    input_datadir = os.environ["FARNIFAUTOGEN_INPUT_DATADIR"] + "/"
else:
#    input_datadir = "./data/"
    input_datadir = "C:/SteamLibrary/steamapps/common/Oblivion/Data/"
if "data/" in input_datadir.lower() or "data\\" in input_datadir.lower():
    input_root = input_datadir.lower().replace("data/","")
    input_root = input_root.lower().replace("data\\","")
else:
    input_root = input_datadir
if (os.environ.get("FARNIFAUTOGEN_OUTPUT_DATADIR") is not None):
    output_datadir = os.environ["FARNIFAUTOGEN_OUTPUT_DATADIR"] + "/"
else:
    output_datadir = "C:/FarNifAutoGen.output/data/"
if "data/" in output_datadir.lower() or "data\\" in output_datadir.lower():
    output_root = output_datadir.lower().replace("data/","")
    output_root = output_root.lower().replace("data\\","")
else:
    output_root = output_datadir
#output_root = outputRoot + "FarNifAutoGen.output/"
#output_datadir = output_root + "data/"
##print "DEBUG: input_datadir = " + input_datadir
##print "DEBUG: input_root = " + input_root
##print "DEBUG: output_datadir = " + output_datadir
##print "DEBUG: output_root = " + output_root
##raw_input()

# set up helper-file variables
blenderFilename = "empty.blend"

# set up multiprocessing settings
try:
    CPU_COUNT = multiprocessing.cpu_count()
except NotImplementedError:
    CPU_COUNT = 1
fullres_collisions = True

# error reporting
error_filename = output_root + "error_list.txt"
def log_error(err_string):
    writemode = 'a'
    if not os.path.exists(error_filename):
        writemode = 'w'
    with open(error_filename, writemode) as error_file:
        error_file.write(err_string + "\n")
def debug_print(err_string):
    global error_filename
    print err_string
    writemode = 'a'
    if not os.path.exists(error_filename):
        writemode = 'w'
    with open(error_filename, writemode) as error_file:
        error_file.write(err_string + "\n")
        error_file.close()

# launch blender
def launchBlender(filename):
    in_file = filename
    conversion_script = "FarNifAutoGen_blender_polyreduce.py"
    ## LOAD BLENDER HERE....
    print "==================="
    print "starting blender..." + in_file
    print "==================="
    #raw_input("DEBUG: PRESS ENTER TO BEGIN")
    rc = subprocess.call([blenderPath, blenderFilename, "-p", "0", "0", "1", "1", "-P", conversion_script, "--", in_file,"--fullres_collisions", str(int(fullres_collisions))])
    if (rc != 0):
        print "Error launching blender: retrying with gui enabled..."
        #raw_input("Press Enter to continue.")
        rc = subprocess.call([blenderPath, blenderFilename, "-p", "0", "0", "1", "1", "-P", conversion_script, "--", in_file,"--fullres_collisions", str(int(fullres_collisions))])
        if (rc != 0):
            print "Unable to launch blender, logging error and skipping file..."
            # log error and continue
            error_list(in_file + " (launch error) could not start blender.")
            return -1

# launch gimp
def launchGIMP(filename):
    scriptfile = "FarNifAutoGen_gimp_lowres"
    bootstrap = "import sys;sys.path=['.']+sys.path;import " + scriptfile + ";" + scriptfile + ".run('" + filename + "')"
    #debug_print("bootstrap=" + bootstrap)
    #print "====GIMP script bootstrap:=======\n" + bootstrap + "\n================\n"
    resultcode = subprocess.call([gimpPath, \
                          "-idf", "--batch-interpreter=python-fu-eval", \
                          "-b", bootstrap])
#    os.remove(joblist)
    if (resultcode != 0):
        debug_print("GIMP processDDS(" + filename + ") ERROR: function failed.")
        #print "ERROR: failed with resultcode=(" + str(resultcode) + ")"
        # log error and continue
#        debug_print(joblist + " failed: resultcode=(" + str(format(resultcode, '08x')) + ")\n")
        return -1
    else:
#        debug_print(joblist + " success.\n")
        return 0  


# main
def main():
    print "Starting FarNifAutoGen..."

    # set up output_dir
    if os.path.exists(output_datadir) == False:
        os.makedirs(output_datadir)

    # reset dds_joblist
    if (os.path.exists(output_root + dds_list_jobfile)):
        os.remove(output_root + dds_list_jobfile)
        ddsjob_stream = open(output_root + dds_list_jobfile, "wb")
        ddsjob_stream.close()

    # read niflist.job
    print "\n1a. Read the nif_list.job file"
    if not os.path.exists(nif_list_jobfile):
        print "no nif joblist found. exiting."
        return()
    else:
        print "joblist found"
    nifjob_stream = open(nif_list_jobfile, "r")
    for line in nifjob_stream:
        line = line.rstrip("\r\n")
        nif_filename, ref_scale = line.split(',')
        if nif_joblist.get(nif_filename) == None:
            nif_joblist[nif_filename] = float(ref_scale)
        else:
            if ref_scale > nif_joblist[nif_filename]:
                nif_joblist[nif_filename] = float(ref_scale)
    nifjob_stream.close()
    
    # for each nif, process nif
    print "\n1b. For each nif, process the nif file"
    if len(nif_joblist) == 0:
        print "job list is empty"
    for filename in nif_joblist:
#        print "processing: " + input_datadir + filename + " ... using ref_scale=" + str(nif_joblist[filename])
        if os.path.exists(input_datadir + filename):
 #           print " file found, calling processNif()..."
            # set global threshold of model radius?
            do_output = FarNifAutoGen_processNif.processNif(filename, ref_scale=nif_joblist[filename], input_datadir_arg=input_datadir, output_datadir_arg=output_datadir)
            # return calculated model radius to figure out to reduce?
            #... call blender polyreducer
            if do_output is True:
#                print " DEBUG: spawn Blender polyreducer"
                launchBlender(FarNifAutoGen_processNif.output_filename_path)
#                raw_input("Press ENTER to continue.")
            else:
#                print "processNIF failed."
                debug_print("processNif(" + filename + ") ERROR: function failed.")
        else:
            debug_print("processNif(" + filename + ") ERROR: file not found.")
#            raw_input("Press ENTER to continue.")

    # read ddslist.job (lowres_list.job)
    print "\n2a. Read the dds job file: " + output_root + dds_list_jobfile
    if not os.path.exists(output_root + dds_list_jobfile):
        print "no dds joblist found. skipping dds processing step."
    else:
        print "joblist found"
        ddsjob_stream = open(output_root + dds_list_jobfile, "r")
        for line in ddsjob_stream:
            dds_filename = line.rstrip("\r\n")
            dds_joblist.append(dds_filename)
        ddsjob_stream.close()
        # for each dds, process dds
#        print "\n2b. For each dds, process the dds file"
        for output_filename in dds_joblist:
            input_filename = output_filename.replace("lowres/", "")
#            print "process dds file: " + input_datadir + input_filename
            if os.path.exists(input_datadir + input_filename):
#                print "  file found."
                folderPath = os.path.dirname(output_datadir + output_filename)
                if os.path.exists(folderPath) == False:
                    os.makedirs(folderPath)
                shutil.copy(input_datadir + input_filename, output_datadir + output_filename)
                # call gimp resizer...
                launchGIMP(output_datadir + output_filename)
            else:
#                print "  file not found, skipping"
                debug_print("processDDS(" + input_filename + ") ERROR: file not found.")
                continue

    # complete
    print "\nFarNifAutoGen complete.\n"
    raw_input("Press ENTER to continue.")

if __name__ == "__main__":
    main()


