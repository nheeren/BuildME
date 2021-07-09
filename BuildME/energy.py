"""
Energy demand algorithm for the RECC building model

Copyright: Niko Heeren, 2019
"""
import datetime
import shutil
import os
import subprocess

import pandas as pd
from tqdm import tqdm

from BuildME import settings, idf




def launch_ep():
    pass


def cleanup_post_sim():
    pass


def gather_files_to_copy(ep_files=settings.ep_exec_files, check=True):
    """
    Collect the neccessary files for copy_files() and check if they exist
    :param idf: The IDF file in question
    :param epw: EPW file in question
    :param ep_files: the e+ files needed for the worker to run
    :param check:
    :return:
    """
    # 1. necessary e+ executable files
    copy_list = [os.path.join(settings.ep_path, f) for f in ep_files]
    # 2. idf e+ input file
    # copy_list.append(os.path.join(settings.archetypes, idf))
    # 3. epw climate file
    # copy_list.append(os.path.join(settings.climate_files_path, epw))
    if check:
        bad_news = [f for f in copy_list if not os.path.exists(f)]
        assert len(bad_news) == 0, "The following files do not exist: %s" % bad_news
    return copy_list


def get_timestamp_path():
    return datetime.datetime.now().strftime("%y%m%d-%H%M%S.%f")


def copy_files(copy_list, tmp_run_path=None, create_dir=True):
    """
    Copies the files to the desired location.
    I guess symlinks could work too, but let's be nice to Windows folks :-P
    :param copy_list: List of files that should be copied, e.g. created with gather_files_to_copy()
    :param tmp_run_path: the subfolder for the simulation run
    :param create_dir: Switch allowing to create new folders
    :param assert_exists: Check if the folder exists
    """
    if not tmp_run_path:
        tmp_run_path = get_timestamp_path()
    run_folder = os.path.join(settings.tmp_path, tmp_run_path)
    if create_dir:
        os.makedirs(run_folder)
    for file in copy_list:
        basename = os.path.basename(file)
        if os.path.splitext(file)[-1] == '.idf':
            basename = 'in.idf'
        elif os.path.splitext(file)[-1] == '.epw':
            basename = 'in.epw'
        shutil.copy2(file, os.path.join(run_folder, basename))
    return tmp_run_path


def delete_ep_files(copy_list, tmp_run_path):
    """
    Deletes the e+ files after simulation, skips input and weather file
    :param tmp_folder:
    :param ep_files:
    """
    run_folder = os.path.join(settings.tmp_path, tmp_run_path)
    for f in copy_list:
        if os.path.basename(f)[-4:] in ['.idf', '.epw']:
            continue
        os.remove(os.path.join(settings.tmp_path, tmp_run_path, os.path.basename(f)))


def delete_temp_folder(tmp_run_path, verbose=False):
    """
    Delete the temporary folder *completely*
    :param tmp_run_path: foldername to delete
    :param verbose: Switch to print a delete confirmation
    """

    # This syntax ensures that this is a subfolder of settings.tmp_path
    shutil.rmtree(os.path.join(settings.tmp_path, tmp_run_path))
    if verbose:
        print("Deleted '%s'" % tmp_run_path)


def run_energyplus_single(tmp_path):
    """
    Runs the model single-threaded
    See docs/energyplus.md for more info
    :param idf_file:
    :param epw_file:
    :return:
    """
    # 1. Run `./ExpandObjects`
    os.chdir(os.path.join(settings.tmp_path, tmp_path))
    # for exec in ['./ExpandObjects', './Basement', './energyplus']:

    with open("log_ExpandObjects.txt", 'w') as log_file:
        subprocess.call('ExpandObjects', shell=True, stdout=log_file, stderr=log_file)
    if os.path.exists('BasementGHTIn.idf'):
        with open("log_Basement.txt", 'w') as log_file:
            subprocess.call('Basement', shell=True, stdout=log_file, stderr=log_file)
        with open('merged.idf', 'w') as merged_idf:
            with open('expanded.idf', 'r') as expanded_idf:
                merged_idf.write(expanded_idf.read())
            with open('EPObjects.txt', 'r') as epobjects:
                merged_idf.write(epobjects.read())
            run_idf = 'merged.idf'
    elif os.path.exists('GHTIn.idf'):
        with open("log_Slab.txt", 'w') as log_file:
            subprocess.call('Slab', shell=True, stdout=log_file, stderr=log_file)
        with open('merged.idf', 'w') as merged_idf:
            with open('expanded.idf', 'r') as expanded_idf:
                merged_idf.write(expanded_idf.read())
            with open('SLABSurfaceTemps.TXT', 'r') as epobjects:
                merged_idf.write(epobjects.read())
        run_idf = 'merged.idf'
    else:
        run_idf = 'expanded.idf'

    # For RT, ExpandObjects wont run?? So testing to add in.idf as run_idf
    if not os.path.exists('expanded.idf'):
        run_idf = 'in.idf'

    with open("log_energyplus.txt", 'w+') as log_file:
        subprocess.call('energyplus -r %s' % run_idf,
                        shell=True, stdout=log_file, stderr=log_file)
        log_file.seek(0)
        if log_file.readlines()[-1] != 'EnergyPlus Completed Successfully.\n':
            print("ERROR: '%s' energy simulation was not successful" % tmp_path)
        log_file.close()
    os.chdir(settings.basepath)


def ep_result_collector(ep_path, save='energy_intensity.csv'):
    """
    Reads the energy plus result file 'eplusout.csv' and returns the result (sum of entire column).
    :param ep_path: Absolute path of 'eplusout.csv'
    :param save: Switch to save the results as CSV.
    :return:
    """
    results_to_collect = ("Heating:EnergyTransfer [J](Hourly)",	"Cooling:EnergyTransfer [J](Hourly)",
                          # Note the trailing whitespace at the end of "InteriorEquipment:Electricity [J](Hourly) "
                          "InteriorLights:Electricity [J](Hourly)", "InteriorEquipment:Electricity [J](Hourly) ")
    ep_file = os.path.join(ep_path, 'eplusout.csv')
    ep_out = pd.read_csv(ep_file)
    results = ep_out.loc[:, results_to_collect].sum()
    if save:
        results.to_csv(os.path.join(ep_path, save), header=False)
    return results


def calc_therm_inertia(fnames):
    """
    Loops through surfaces and calculates their thermal mass.
    Based on https://unmethours.com/question/39167/is-there-a-way-to-extract-thermal-mass-from-an-energyplus-model/
    :return:
    """
    tq = tqdm(fnames, desc='Initiating...', leave=True)
    for fname in tq:
        tq.set_description(fname)
        run_path = os.path.join(settings.tmp_path, fname)
        idff = idf.read_idf(os.path.join(run_path, 'in.idf'))
        surfaces = idf.get_surfaces(idff, fnames[fname]['energy_standard'][2], fnames[fname]['RES'][2])
        total_heat_capacity = 0
        for stype in surfaces:
            for surface in surfaces[stype]:
                construction_heat_capacity = 0

                construction = idff.getobject('CONSTRUCTION', surface.Construction_Name)

                # get the field names, which in eppy is a list of
                # ['key', 'Name', 'Outside_Layer', 'Layer_2', ... 'Layer_10']
                construction_field_names = construction.fieldnames

                # loop through the construction's field names (layers),
                # skipping first and second (key and Name)
                for field_name in construction_field_names[2:]:

                    # get the material object from the layer
                    attribute = field_name
                    material_name = getattr(construction, attribute)
                    material = idff.getobject('MATERIAL', material_name)

                    # calculate the material's heat capacity and add it to the construction's
                    if material is not None:
                        thickness = material.Thickness
                        density = material.Density
                        specific_heat = material.Specific_Heat
                        material_heat_capacity = thickness * density * specific_heat
                        construction_heat_capacity += material_heat_capacity

                # add the construction's total heat capacity to the model's total
                total_heat_capacity += construction_heat_capacity

        print(fname, 'J/m2*K =', total_heat_capacity)

