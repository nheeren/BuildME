
from BuildME import settings,  __version__
import itertools
import os
import datetime
import json
import pickle


def create_batch_simulation(combinations):
    """
    Creates a dictionary 'batch_sim' and create a folder structure to store the simulation results
    :param combinations: a dictionary with the selected BuildME aspects and their values
    :returns: batch_sim: dictionary with batch simulation information
    :returns: run: batch simulation identifier
    """
    print("Creating batch simulation")
    run = datetime.datetime.now().strftime("%y%m%d-%H%M%S")
    # combinations = settings.debug_combinations
    default_aspects = ['occupation', 'en-std', 'res', 'climate_region', 'climate_scenario', 'cooling']
    batch_sim = {}
    for region in combinations:
        keys = list(combinations[region].keys())
        values = list(combinations[region].values())
        new_aspects = [k for k in keys if k not in default_aspects]
        for comb in itertools.product(*values):
            comb_dict = {k: comb[i] for i, k in enumerate(keys)}
            sim = region+'_'+'_'.join(comb)
            # get default aspects (if one doesn't exist, set as None)
            for aspect in default_aspects:
                try:
                    comb_dict[aspect]
                except KeyError:
                    comb_dict[aspect] = None
            replace_dict = {asp: comb_dict[asp] for asp in ['en-std', 'res'] if comb_dict[asp] is not None}
            # get new aspects
            for asp in new_aspects:
                replace_dict[asp] = comb_dict[asp]
            for asp in ['occupation', 'climate_scenario', 'climate_region']:
                if comb_dict[asp] is None:
                    raise Exception(f'Aspect {asp} was not found but is required for simulation')
            # choose archetype idf file
            if comb_dict['cooling'] == 'MMV':
                cool_str = '_auto-MMV'
            else:
                cool_str = ''
            if (region, comb_dict['occupation']) in settings.archetype_proxies:
                region_proxy, occ_type_proxy = settings.archetype_proxies[(region, comb_dict['occupation'])]
                idf_choice = os.path.join(settings.archetypes, region_proxy, occ_type_proxy + cool_str + '.idf')
            else:
                idf_choice = os.path.join(settings.archetypes, region, comb_dict['occupation'] + cool_str + '.idf')
            # choose weather epw file
            epw_choice = os.path.join(settings.climate_files_path, comb_dict['climate_scenario'],
                                      settings.climate_stations[region][comb_dict['climate_region']])
            # choose folder for simulation results
            folder_choice = os.path.join(settings.tmp_path, run, sim)

            batch_sim[sim] = {'climate_file': epw_choice, 'archetype_file': idf_choice, 'run_folder': folder_choice,
                             'replace_dict': replace_dict}
            for k, v in comb_dict.items():
                batch_sim[sim][k] = v

    create_base_folder(run, combinations, batch_sim)
    create_subfolders(batch_sim, run)
    return batch_sim, run


def create_base_folder(run, combinations, batch_sim):
    """
    Creates the base folder where simulations are stored and creates a run-specific txt file.
    :param run: batch simulation identifier
    :param combinations: a dictionary with the selected BuildME aspects and their values
    :param batch_sim: dictionary with batch simulation information
    """
    bpath = os.path.join(settings.tmp_path, run)
    # create folder
    os.makedirs(bpath)
    cfile = os.path.join(bpath, "%s_config.txt" % run)
    with open(cfile, 'w') as conf_file:
        conf_file.write("BuildME v%s\n\n" % __version__)
        conf_file.write("Run folder:\n %s\n\n\n" % bpath)
        conf_file.write("Config variable (typically 'settings.combinations'):\n\n")
        conf_file.write(json.dumps(combinations, indent=4))
        conf_file.write("\n\n\nEffective config and paths:\n\n")
        conf_file.write(json.dumps(batch_sim, indent=4))
        conf_file.write("\n")
        conf_file.close()


def create_subfolders(batch_sim, run):
    """
    Creates a subfolder for each building instance in the batch simulation
    :param batch_sim: dictionary with batch simulation information
    :param run: batch simulation identifier
    """
    for sim in batch_sim:
        fpath = os.path.join(settings.tmp_path, run, sim)
        # create folder
        os.makedirs(fpath)
    # save list of all folders
    scenarios_filename = os.path.join(settings.tmp_path, run + '.run')
    pickle.dump(batch_sim, open(scenarios_filename, "wb"))
    return


def find_and_load_last_run(path=settings.tmp_path):
    """
    Finds the last batch simulation run as saved in create_batch_simulation().
    :param path: folder to scan for simulation files
    :returns: batch_sim: dictionary with batch simulation information
    """
    candidates = [f for f in os.listdir(path) if f.endswith('.run')]
    if len(candidates) == 0:
        raise FileNotFoundError("Couldn't find any .run files in %s" % path)
    run_file = os.path.join(path, sorted(candidates)[-1])
    print("Loading datafile '%s'" % run_file)
    batch_sim = pickle.load(open(run_file, 'rb'))
    return batch_sim
