"""
Functions to perform the actual simulations.

Copyright: Niko Heeren, 2019
"""
import collections
import datetime
import multiprocessing as mp
import os
import shutil
import pickle
from time import sleep

import pandas as pd
from tqdm import tqdm

from BuildME import settings, idf, material, energy, mmv, __version__


def create_combinations(comb=settings.combinations):
    """
    Creates permutations of files to be simulated / calculated.
    The foldernames are coded as follows and separated by underscores: World Region, Occupation archetype,
    energy standard, Resource Efficiency Strategy RES, climate region, and climate scenario.
    An example for the USA, single-family home, standard energy efficiency, no RES, in US climate region 1A,
    and with the climate scenario of 2015 (i.e. none): US_SFH_standard_RES0_cr1A_2015
    :return:
    """
    print("Creating scenario combinations")
    fnames = {}
    # 1 Region
    for region in [r for r in comb if r != 'all']:
        # 2 archetype
        for occ_type in comb[region]['occupation']:
            # 3 energy standard
            for energy_std in comb[region]['energy standard']:
                # 'informal' type only has 'non-standard' -- skip other combinations
                if occ_type == 'informal' and energy_std in ['standard', 'efficient', 'ZEB']:
                    continue
                # 4 Resource Efficiency Strategy
                for res in comb[region]['RES']:
                    # 5 Climate region
                    for climate_reg in comb[region]['climate_region']:
                        # 6 Climate scenario
                        for climate_scen in comb[region]['climate_scenario']:
                            for cool in comb[region]['cooling']:
                                fname = '_'.join([region, occ_type, energy_std, res, climate_reg, climate_scen, cool])
                                fnames[fname] = \
                                    {
                                    'climate_file': os.path.join(settings.climate_files_path, climate_scen,
                                                                 settings.climate_stations[region][climate_reg]),
                                    'archetype_file': os.path.join(settings.archetypes, region, occ_type + '.idf'),
                                    'energy_standard': [region, occ_type, energy_std],
                                    'RES': [region, occ_type, res],
                                    'region': region,
                                    'occupation': occ_type,
                                    'cooling': cool,
                                    'run_folder': os.path.join(settings.tmp_path, fname)
                                    }
                                # make sure no underscores are used in the pathname, because this could cause issues later
                                assert list(fnames)[-1].count('_') == 6, \
                                    "Scenario combination names mustn't use underscores: '%s'" % fnames[-1]
    return fnames


def nuke_folders(fnames, forgive=True):
    """
    Deletes all folders specified in the `fnames` variable.
    :param forgive: will continue also if certain folder's don't exist
    :param fnames: List of foldernames as created by create_combinations()
    :return:
    """
    for fname in fnames:
        fpath = os.path.join(settings.tmp_path, fname)
        if not os.path.exists(fpath) and forgive:
            continue
        shutil.rmtree(fpath)
    remaining_folders = [x[0] for x in os.walk(settings.tmp_path)][1:]
    if len(remaining_folders) > 0:
        print("INFO: './tmp' folder not empty: %s" % ', '.join(remaining_folders))


def apply_obj_name_change(idf_data, replacer, replace_str):
    """
    Replaces the all 'Construction' objects in the IDF with the current energy standard version.
    :param archetype_file:
    :param replacer:
    """

    # If the windows are modeled in FenestrationSurface:Detailed instead of Window object
    if 'FENESTRATIONSURFACE:DETAILED' in [x for x in idf_data.idfobjects]:
        objects = ['FenestrationSurface:Detailed', 'BuildingSurface:Detailed', 'Door', 'Window']
    else:
        objects = ['Window', 'BuildingSurface:Detailed', 'Door']
    # Load IDF file
    for obj_type in objects:
        for obj in idf_data.idfobjects[obj_type.upper()]:
            if replace_str in obj.Construction_Name:
                # replace the item
                obj.Construction_Name = obj.Construction_Name.replace(replace_str, '-' + replacer[2])
    # idf_data.idfobjects['Building'.upper()][0].Name = '.'.join(replacer)
    return idf_data


def apply_rule_from_excel(idf_f, res, en_replace):
    """

    :param idf_f:
    :param res:
    :param en_replace: Excel replacement rules
    :return:
    """
    xls_values = en_replace.loc(axis=0)[[res[0]], [res[1]], [res[2]]]
    if not 'RES' in res[2]:
        assert len(xls_values) > 0, "Did not find an energy replacement for '%s" % res
    for xls_value in xls_values.iterrows():
        if xls_value[1]['Value'] == 'skip':
            print("bam")
            continue
        for idfobj in idf_f.idfobjects[xls_value[1]['idfobject'].upper()]:
        # TODO: Seems like this skips replacement of values for MFH? Changed replace.xlsx file..
            if idfobj.Name not in ('*', xls_value[1].Name):
                continue
            setattr(idfobj, xls_value[1]['objectfield'], xls_value[1]['Value'])
    return idf_f


def copy_scenario_files(fnames, replace=False):
    """
    Creates scenario folders and copies the necessary files (climate and IDF file) into them. Further,
    it applies the energy standard and RES scenario to the IDF archetype.
    :param replace:
    :type fnames: List of combinations / foldernames as created by create_combinations()
    :return:
    """
    if replace:
        print("DELETING %i folders..." % len(fnames))
        nuke_folders(fnames)
    print("Copying files...")
    res_replace = pd.read_excel('./data/replace.xlsx', index_col=[0, 1, 2], sheet_name='RES')
    tq = tqdm(fnames, leave=True)
    for fname in tq:
        # tq.set_description(fname)
        fpath = os.path.join(settings.tmp_path, fname)
        # create folder
        os.makedirs(fpath)
        # copy climate file
        shutil.copy(fnames[fname]['climate_file'], os.path.join(fpath, 'in.epw'))
        # copy IDF archetype file
        idf_f = idf.read_idf(fnames[fname]['archetype_file'])
        if fnames[fname]['cooling'] == 'MMV':
            print("\nChanging the archetype to one with MMV (cooling through HVAC + window opening)")
            idf_f = mmv.change_archetype_to_MMV(idf_f, fnames[fname])
        en_replace = pd.read_excel('./data/replace.xlsx', index_col=[0, 1, 2], sheet_name='en-standard')
        idf_f = apply_obj_name_change(idf_f, fnames[fname]['energy_standard'],
                                       '-en-std-replaceme')
        idf_f = apply_obj_name_change(idf_f, fnames[fname]['RES'],
                                       '-res-replaceme')
        idf_f = apply_rule_from_excel(idf_f, fnames[fname]['energy_standard'], en_replace)
        idf_f = apply_rule_from_excel(idf_f, fnames[fname]['RES'], res_replace)
        idf_f.idfobjects['Building'.upper()][0].Name = fname
        idf_f.saveas(os.path.join(fpath, 'in.idf'))
    # save list of all folders
    scenarios_filename = os.path.join(settings.tmp_path, datetime.datetime.now().strftime("%y%m%d-%H%M%S") + '.run')
    # pd.DataFrame(fnames.keys()).to_csv(scenarios_filename, index=False, header=False)
    pickle.dump(fnames, open(scenarios_filename, "wb"))
    return scenarios_filename


def find_last_run(path=settings.tmp_path):
    """
    Returns the last scenario combination run as saved in copy_scenario_files().
    :param path: folder to scan
    :return: filename, e.g. '190403-230346.run'
    """
    candidates = [f for f in os.listdir(path) if f.endswith('.run')]
    if len(candidates) == 0:
        raise FileNotFoundError("Couldn't find any .run files in %s" % path)
    return os.path.join(path, sorted(candidates)[-1])


def load_run_data_file(filename):
    """
    Returns the last scenario combination run as saved in copy_scenario_files().
    :param filename: Absolute filename
    :return: filename, e.g. '190403-230346.run'
    """
    print("Loading datafile '%s'" % filename)
    return pickle.load(open(filename, 'rb'))


def translate_to_odym_mat(total_material_mass):
    res = {}
    for mat in total_material_mass:
        if settings.odym_materials[mat] not in res:
            res[settings.odym_materials[mat]] = total_material_mass[mat]
        else:
            res[settings.odym_materials[mat]] += total_material_mass[mat]
    return res


def calculate_materials(fnames=None):
    print("Extracting materials and surfaces...")
    if not fnames:
        fnames = load_run_data_file(find_last_run())
    fallback_materials = material.load_material_data()
    tq = tqdm(fnames, desc='Initiating...', leave=True)
    for folder in tq:
        tq.set_description(folder)
        run_path = os.path.join(settings.tmp_path, folder)
        idff = material.read_idf(os.path.join(run_path, 'in.idf'))
        materials = material.read_materials(idff)
        materials_dict = material.make_materials_dict(materials)
        densities = material.make_mat_density_dict(materials_dict, fallback_materials)
        constructions = material.read_constructions(idff)
        mat_vol_m2 = material.calc_mat_vol_m2(constructions, materials_dict, fallback_materials)

        # If RT archetype, need to account for zone multipliers
        if fnames[folder]['energy_standard'][1] == 'RT':
            surfaces = material.get_surfaces_with_zone_multiplier(idff, fnames[folder]['energy_standard'][2],
                                             fnames[folder]['RES'][2])
        else:
            surfaces = material.get_surfaces(idff, fnames[folder]['energy_standard'][2],
                                             fnames[folder]['RES'][2])

        mat_vol_bdg = material.calc_mat_vol_bdg(idff, surfaces, mat_vol_m2)
        total_material_mass = material.calc_mat_mass_bdg(mat_vol_bdg, densities)

        odym_mat = translate_to_odym_mat(total_material_mass)
        surface_areas = material.calc_surface_areas(surfaces)
        # material_intensity = material.calc_material_intensity(total_material_mass, reference_area)
        res = odym_mat
        res['floor_area_wo_basement'] = surface_areas['floor_area_wo_basement']
        res['footprint_area'] = surface_areas['footprint_area']

        # TODO: generalise the addition of structural components
        if fnames[folder]['energy_standard'][1] == 'SFH-small-concrete' or fnames[folder]['energy_standard'][1] == 'SFH-small-masonry':
            if 'RES2.1' in fnames[folder]['RES'][2]:
                postbeam = add_surrogate_beams(fnames[folder]['RES'][2], surface_areas['ext_wall'])
                res[postbeam[0]] += postbeam[1]

        # If small SFH (1 floor) no steel beams should be added, only for SFH (two floors) or MFH (3 floors)
        if 2 <= res['floor_area_wo_basement'] / res['footprint_area'] < 15:
            loadbeam = add_surrogate_beams(fnames[folder]['RES'][2], res['floor_area_wo_basement'])
            if loadbeam[0] in res:
                res[loadbeam[0]] += loadbeam[1]
            else:
                res[loadbeam[0]] = loadbeam[1]
            if 'RES2.1' in fnames[folder]['RES'][2]:
                postbeam = add_surrogate_beams(fnames[folder]['RES'][2], surface_areas['ext_wall'])
                res[postbeam[0]] += postbeam[1]

        # If building with more than 15 floors: modeled with columns, shear walls, flat slabs and larger foundation..
        if res['floor_area_wo_basement']/res['footprint_area'] > 15:
            columns = add_surrogate_columns(fnames[folder]['RES'][2], res['floor_area_wo_basement'], res['footprint_area'])
            foundation = add_foundation(res['footprint_area'])

            # Iterating through columns dict with concrete and steel since reinforced concrete
            for k, v in columns.items():
                if k in res:
                    res[k] += v
                else:
                    res[k] = v

            for k, v in foundation.items():
                if k in res:
                    res[k] += v
                else:
                    res[k] = v
            # If wooden version light wall steel studs and steel beams are added for the roof
            if fnames[folder]['RES'][2] == 'RES2.1' or fnames[folder]['RES'][2] == 'RES2.1+RES2.2':
                lightwall_steel = add_steel_lightwall(fnames[folder]['RES'][2], res['floor_area_wo_basement'], res['footprint_area'])
                roof_beams = add_surrogate_roof_beams(fnames[folder]['RES'][2], res['footprint_area'])
                if lightwall_steel[0] in res:
                    res[lightwall_steel[0]] += lightwall_steel[1]
                else:
                    res[lightwall_steel[0]] = lightwall_steel[1]

                if roof_beams[0] in res:
                    res[roof_beams[0]] += roof_beams[1]
                else:
                    res[roof_beams[0]] = roof_beams[1]

        material.save_materials(res, run_path)

def add_surrogate_beams(res, area, distance=0.6,):
    res_dict = {'RES0': {'Material': 'construction grade steel', 'vol': .05*.05, 'density': 8050},
                'RES2.1': {'Material': 'wood and wood products', 'vol': .12*.26, 'density': 500},
                'RES2.2': {'Material': 'construction grade steel', 'vol': .04*.04, 'density': 8050},
                'RES2.1+RES2.2': {'Material': 'wood and wood products', 'vol': .12*.20, 'density': 500}}
    side_length = area ** 0.5
    number_beams = side_length / distance + 1
    res_vol = res_dict[res]['vol'] * side_length * number_beams
    mass = res_vol * res_dict[res]['density']
    return res_dict[res]['Material'], mass

#TODO: Change floor system to slab + beam instead of flat slab? See Gan et al.(2019)
'''def add_surrogate_beams_slabs(res, area, distance=0.2,):
    res_dict = {'RES0': {'Material': 'construction grade steel', 'vol': .012*.012, 'density': 8050},
                'RES2.2': {'Material': 'construction grade steel', 'vol': .012*.012, 'density': 8050}}
    side_length = area ** 0.5
    number_beams = side_length / distance + 1
    res_vol = res_dict[res]['vol'] * side_length * number_beams
    mass = res_vol * res_dict[res]['density']
    return res_dict[res]['Material'], mass'''

def add_surrogate_postbeams(res, area, distance=0.6,):
    res_dict = {'RES2.1': {'Material': 'wood and wood products', 'vol': .1*.05, 'density': 500},
                'RES2.1+RES2.2': {'Material': 'wood and wood products', 'vol': .1*.04, 'density': 500}}
    side_length = area ** 0.5
    number_beams = side_length / distance + 1
    res_vol = res_dict[res]['vol'] * side_length * number_beams
    mass = res_vol * res_dict[res]['density']
    return res_dict[res]['Material'], mass

def add_surrogate_columns(res, floor_area, footprint_area, room_h = 3):
    """
    Function to add columns to the perimeter of the building. Dimensions for RT is taken from Taranth: Reinforced concrete
    buildings, p. 219. Use the average column size of the middle floor approx.
    Reinforcement ratio in columns is assumed to be 2.5-3% of the volume of concrete, based on Foraboschi et al. (2014).
    #TODO: parameterise the size of columns depending on height of the buildings, spacing between columns etc.
    :param res: scenario, RES0, RES2.1 etc.
    :param floor_area: total floor area of building
    :param footprint_area: footprint area of building
    :param distance: spacing between columns in meters, book "Design of Tall Buildings" and Kim et al. (2008)
    param room_h: height of room
    :return: returns materials of columns and total mass
    """
    res_dict = {'RES0': {'Material': {'construction grade steel': {'vol': 0.03 * .950 * .750 * room_h, 'density': 7850},
                                      'concrete': {'vol': .950 * .750 * room_h, 'density': 2400}}},
                'RES2.1': {
                    'Material': {'construction grade steel': {'vol': 0.03 * .50 * .50 * room_h, 'density': 7850},
                                 'concrete': {'vol': .50 * .50 * room_h, 'density': 2400},
                                 'wood and wood products': {'vol': .30 * .30 * room_h, 'density': 500}}},
                'RES2.2': {'Material': {'construction grade steel': {'vol': 0.03 * .950 * .750 * room_h, 'density': 7850},
                                        'concrete': {'vol': .950 * .750 * room_h, 'density': 2400}}},
                'RES2.1+RES2.2': {
                    'Material': {'construction grade steel': {'vol': 0.03 * .50 * .50 * room_h, 'density': 7850},
                                 'concrete': {'vol': .50 * .50 * room_h, 'density': 2400},
                                 'wood and wood products': {'vol': .265 * .215 * room_h, 'density': 500}}}}

    perimeter = footprint_area ** 0.5 * 4
    floors = floor_area / footprint_area

    if res == 'RES0' or res == 'RES2.2':
        distance = 9
        number_columns = (perimeter / distance + 1)*floors

    if res == 'RES2.1' or res == 'RES2.1+RES2.2':
        distance = 3
        number_columns_wood = (footprint_area/3**2)*(floors-2) # keep the concrete columns on the two lower floors
        number_columns_reinforced = (footprint_area/3**2)*2

    mat = dict()
    for outer_k, outer_v in res_dict[res]['Material'].items():
        if res == 'RES2.1' or res == 'RES2.1+RES2.2':
            if outer_k == 'concrete' or outer_k == 'construction grade steel':
                mat.update({outer_k: outer_v['vol'] * outer_v['density'] * number_columns_reinforced})
            else:
                mat.update({outer_k: outer_v['vol'] * outer_v['density'] * number_columns_wood})
        else:
            mat.update({outer_k: outer_v['vol'] * outer_v['density'] * number_columns})

    return mat


def add_steel_lightwall(res, floor_area, footprint_area, distance=0.4, room_h = 3):
    """
    Function to add light gauge steel wall for the wooden versions of the RT building.

    """
    res_dict = {'RES2.1': {'Material': 'construction grade steel', 'vol': .15 * .0005, 'density': 8050},
                'RES2.1+RES2.2': {'Material': 'construction grade steel', 'vol': .15 * .0005, 'density': 8050}}
    perimeter = footprint_area ** 0.5 * 4
    floors = floor_area/footprint_area

    number_vertical = perimeter / distance + 1
    mass_horizontal_members = res_dict[res]['vol'] * room_h * number_vertical * res_dict[res]['density'] * floors
    mass_vertical_members = res_dict[res]['vol'] * perimeter * 2 * res_dict[res]['density'] * floors

    return res_dict[res]['Material'], mass_horizontal_members+mass_vertical_members

def add_surrogate_roof_beams(res, footprint_area, distance=3,):
    """
    Function to add surrogate roof beams as for wooden RT building (as in Tallwood House, see doc)
    """
    res_dict = {'RES2.1': {'Material': 'construction grade steel', 'vol': .25*.25, 'density': 8050},
                'RES2.1+RES2.2': {'Material': 'construction grade steel', 'vol': .20*.20, 'density': 8050}}

    side_length = footprint_area ** 0.5
    number_beams = side_length / distance + 1
    res_vol = res_dict[res]['vol'] * side_length * number_beams
    mass = res_vol * res_dict[res]['density']

    return res_dict[res]['Material'], mass

def add_foundation(footprint_area):
    """
    Function to add foundation for the high-rise buildings. 0.6 m3 concrete per footprint area and
    100 kg steel per m3 concrete based on lit.review, see doc.
    """
    concrete_intensity = 0.6 # m3 concrete per footprint area
    steel_intensity = 100 # kg steel per m3 concrete
    density_concrete = 2400
    vol_concrete = footprint_area * concrete_intensity
    mass_concrete = vol_concrete * density_concrete
    mass_steel = vol_concrete * steel_intensity

    return dict(zip(['concrete', 'construction grade steel'], [mass_concrete, mass_steel]))

def calculate_energy(fnames=None):
    print("Perform energy simulation...")
    if not fnames:
        fnames = load_run_data_file(find_last_run())
    tq = tqdm(fnames, desc='Initiating...', leave=True)
    for folder in tq:
        run_path = os.path.join(settings.tmp_path, folder)
        tq.set_description(folder)
        copy_us = energy.gather_files_to_copy()
        # TODO: Change Building !- Name
        tmp = energy.copy_files(copy_us, tmp_run_path=folder, create_dir=False)
        energy.run_energyplus_single(tmp)
        energy.delete_ep_files(copy_us, tmp)


def calculate_energy_mp(fnames=None, cpus=mp.cpu_count()-1):
    print("Perform energy simulation on %s CPUs..." % cpus)
    if not fnames:
        fnames = load_run_data_file(find_last_run())
    pool = mp.Pool(processes=cpus)
    m = mp.Manager()
    q = m.Queue()
    pbar = tqdm(total=len(fnames), smoothing=0.1, unit='sim')
    args = ((folder, q, no) for no, folder in enumerate(fnames))
    result = pool.map_async(calculate_energy_worker, args)
    old_q = 0
    while not result.ready():
        #pbar.update()
        #print(q.qsize())
        if q.qsize() > old_q:
            pbar.update(q.qsize() - old_q)
        else:
            pbar.update(0)
        old_q = q.qsize()
        sleep(0.2)
    pool.close()
    pool.join()
    pbar.close()
    result_output = result.get()


def calculate_energy_worker(args):
    folder, q, no = args
    run_path = os.path.join(settings.tmp_path, folder)
    # sleep(1.5)
    copy_us = energy.gather_files_to_copy()
    tmp = energy.copy_files(copy_us, tmp_run_path=folder, create_dir=False)
    energy.run_energyplus_single(tmp)
    energy.delete_ep_files(copy_us, tmp)
    q.put(no)


def simulate_all(fnames):
    """
    Launches the simulations.
    :return:
    """
    # scenarios = pd.read_csv(scenarios_csv)
    calculate_materials(fnames)
    # calculate_energy()
    pass


def collect_logs(fnames, logfile='eplusout.err'):
    """
    Goes through all folders and extracts the last line of the energyplus log file to make sure the simulation was successful.
    :param fnames:
    :param logfile:
    :return:
    """
    print('Collecting E+ logs...')
    res = {}
    for folder in tqdm(fnames):
        res[folder] = {}
        file = os.path.join(fnames[folder]['run_folder'], logfile)
        with open(file, "rb") as f:
            # https://stackoverflow.com/a/18603065/2075003
            # first = f.readline()  # Read the first line.
            f.seek(-2, os.SEEK_END)  # Jump to the second last byte.
            while f.read(1) != b"\n":  # Until EOL is found...
                f.seek(-2, os.SEEK_CUR)  # ...jump back the read byte plus one more.
            last = f.readline()  # Read last line.
            res_string = last.decode("utf-8")
            for repl in [('*', ''), ('  ', ''), ('\n', '')]:
                res_string = res_string.replace(*repl)
            res[folder]['ep_log'] = res_string
    return res


def load_material(fnames):
    print('Loading Material results...')
    res = {}
    for folder in tqdm(fnames):
        df = pd.read_csv(os.path.join(fnames[folder]['run_folder'], 'materials.csv'), header=None)
        res[folder] = {d[1][0]: d[1][1] for d in df.iterrows()}
        res[folder]['total_mat'] = df.sum(axis=0)[1]
    return res


def collect_energy(fnames):
    print('Collecting Energy results...')
    res = {}
    for folder in tqdm(fnames):
        energy_res = energy.ep_result_collector(os.path.join(fnames[folder]['run_folder']))

        res[folder] = energy_res.to_dict()
    return res


def disaggregate_scenario_str(in_dict, unstack_cols):
    """
    Converting scenario titles, separated by underscores, into columns.
    Also re-arranging dataframe.
    :param in_dict:
    :param unstack_cols:
    :return:
    """
    res = pd.DataFrame.from_dict(in_dict, orient='index')
    res.index = pd.MultiIndex.from_tuples(tuple(res.index.str.split('_')))
    res.index.names = ['region', 'occupation', 'energy_std', 'RES', 'climate_reg', 'IPCC_scen']
    res = res.unstack(unstack_cols)
    return res


def weighing_climate_region(res):
    """
    Multiplies each result by its climate region ratio given in aggregate.xlsx.
    :param res:
    :return:
    """
    weights = pd.read_excel('./data/aggregate.xlsx', sheet_name='climate_reg', index_col=[0, 1])
    # making sure index is all strings
    weights.index = pd.MultiIndex.from_tuples([(ix[0], str(ix[1])) for ix in weights.index.tolist()])
    # I know looping DFs is lame, but who can figure out this fricking syntax?!
    #  https://stackoverflow.com/a/41494810/2075003
    for region in res.index.levels[0]:
        # Why u not update the column index pandas??
        for cr in set([c[1] for c in res.loc[region].dropna(axis=1)]):
            if cr == '':
                continue
            if cr == 'Brazil':
                region = 'Oth-LAM'
                cr = 'Brazil'
                res.loc[pd.IndexSlice[region, :, :], pd.IndexSlice[:, cr]] = \
                    res.loc[pd.IndexSlice[region, :, :], pd.IndexSlice[:, cr]] * \
                    weights.loc[pd.IndexSlice[region, cr], 'share']

            res.loc[pd.IndexSlice[region, :, :], pd.IndexSlice[:, cr]] = \
                res.loc[pd.IndexSlice[region, :, :], pd.IndexSlice[:, cr]] * \
                weights.loc[pd.IndexSlice[region, cr], 'share']
    return res


def weighing_energy_carrier(ei_result):
    energy_dict = {'Cooling': 'Cooling:EnergyTransfer [J](Hourly)',
                   'Heating': 'Heating:EnergyTransfer [J](Hourly)'}
    weights = pd.read_excel('./data/aggregate.xlsx', sheet_name='energy_carrier', index_col=[0])
    ei_result.index = ei_result.index.droplevel(4)
    # Can't believe there is no easier way... https://stackoverflow.com/a/42612344/2075003
    df = pd.DataFrame(data=0.0, index=ei_result.index, columns=['Heating', 'Cooling', 'DHW']).stack()
    df = pd.DataFrame(data=0.0, index=df.index, columns=weights.columns).stack()
    df.index.names = ei_result.index.names + ['ServiceType', 'energy_carrier']
    for i, s in df.iteritems():
        if i[4] in ('Heating', 'Cooling'):
            df[i] = ei_result.loc[i[:-2], [energy_dict[i[4]]]].sum() * \
                    weights.loc[i[0], i[-1]]
        elif i[4] == 'DHW':
            df[i] = ei_result.loc[i[:-2], ['DHW']] * weights.loc[i[0], i[-1]]
        else:
           df[i] = 0.0
    return df


def divide_by_area(energy, material_surfaces, multi=1.0, ref_area='floor_area_wo_basement'):
    res = {}
    for scenario in energy:
        res[scenario] = {}
        area = material_surfaces[scenario][ref_area]
        for e in energy[scenario]:
            res[scenario][e] = energy[scenario][e] / area * multi
    return res


def save_ei_result(energy, material_surfaces, ref_area='floor_area_wo_basement'):
    """

    :param res:
    :param ref_area:
    :return:
    """
    res = divide_by_area(energy, material_surfaces, 1/10**6, ref_area)
    res = disaggregate_scenario_str(res, ['climate_reg'])
    res = weighing_climate_region(res)
    res = add_DHW(res)
    writer = pd.ExcelWriter(find_last_run().replace('.run', '_ei.xlsx'), engine='xlsxwriter')
    res.to_excel(writer, 'all')
    res['Heating:EnergyTransfer [J](Hourly)'].sum(axis=1).to_excel(writer, 'heat')
    res['Cooling:EnergyTransfer [J](Hourly)'].sum(axis=1).to_excel(writer, 'cool')
    res['InteriorLights:Electricity [J](Hourly)'].sum(axis=1).to_excel(writer, 'light')
    res['InteriorEquipment:Electricity [J](Hourly) '].sum(axis=1).to_excel(writer, 'equip')
    (res['InteriorEquipment:Electricity [J](Hourly) '].sum(axis=1) +
     res['InteriorLights:Electricity [J](Hourly)'].sum(axis=1)).to_excel(writer, 'elec_total')
    res['DHW'].to_excel(writer, 'DHW')
    res.sum(axis=1).to_excel(writer, 'total')
    writer.save()
    return res

# Andrea: assume the same for RT as for MFH for now...
def add_DHW(ei, dhw_dict={'MFH': 75, 'SFH': 50, 'informal': 50, 'RT': 75, 'SFH-small-concrete': 50, 'SFH-small-masonry': 50, 'SFH-small-wood': 50, 'MFH-masonry': 75, 'SFH-masonry': 50}):
    for occ in dhw_dict:
        if occ in ei.index.levels[1]:
            ei.loc[pd.IndexSlice[:, occ, :, :], 'DHW'] = dhw_dict[occ]
    return ei


def save_mi_result(material_surfaces):
    res = divide_by_area(material_surfaces, material_surfaces)
    res = disaggregate_scenario_str(res, ['climate_reg'])
    res.to_excel(find_last_run().replace('.run', '_mi.xlsx'))
    return res


def save_ei_for_odym(ei_result):
    res = weighing_energy_carrier(ei_result)
    res.index = res.index.set_levels([settings.odym_regions[r] for r in res.index.levels[0]], 0)
    new_idx_names = ['Products', 'Use_Phase_i4', 'RES', 'Service', 'SSP_Regions_32', 'Energy carrier']
    new_idx = [tuple(['_'.join((i[1], i[2]))] + ['Energy Intensity UsePhase'] + [i[n] for n in (3, 4, 0, 5)])
               for i in res.index.values]
    res.index = pd.MultiIndex.from_tuples(new_idx, names=new_idx_names)
    res = pd.DataFrame(res, columns=['Value'])
    res['Unit'] = 'MJ/m2/yr'
    res['Stats_array_string'] = ''
    res['Comment'] = 'Simulated in BuildME v%s' % __version__
    # some more stuff?
    res.to_excel(find_last_run().replace('.run', '_ODYM_ei.xlsx'), merge_cells=False)
    print("Wrote '%s'" % find_last_run().replace('.run', '_ODYM_ei.xlsx'))


def save_mi_for_odym(mi_result):
    # Only use the first climate region
    mi_result.index = mi_result.index.set_levels([settings.odym_regions[r] for r in mi_result.index.levels[0]], 0)
    # mi_result = mi_result.loc[pd.IndexSlice[:, :, :, :, :], pd.IndexSlice[:, mi_result.columns.levels[1][0]]]
    new_mi = pd.DataFrame(index=mi_result.index, columns=mi_result.columns.levels[0])
    for region in mi_result.index.levels[0]:
        first_climate_region = settings.combinations[dict([[v,k] for k,v in settings.odym_regions.items()])[region]]['climate_region'][0]
        new_mi.loc[region] = mi_result.loc[region, pd.IndexSlice[:, first_climate_region]].values
        # mi_result.columns = mi_result.columns.droplevel(1)
    new_mi = new_mi[[c for c in new_mi.columns if c not in ['floor_area_wo_basement', 'footprint_area', 'total_mat']]]
    new_mi.index = new_mi.index.droplevel(4)
    new_mi = new_mi.stack()
    new_idx_names = ['Products', 'Use_Phase_i4', 'RES', 'Engineering_Materials_m2', 'SSP_Regions_32']
    new_idx = [tuple(['_'.join((i[1], i[2]))] + ['Material Intensity UsePhase'] + [i[n] for n in (3,  4, 0)])
               for i in new_mi.index.values]
    new_mi.index = pd.MultiIndex.from_tuples(new_idx, names=new_idx_names)
    new_mi = pd.DataFrame(new_mi, columns=['Value'])
    new_mi['Unit'] = 'kg/m2'
    new_mi['Stats_array_string'] = ''
    new_mi['Comment'] = 'Simulated in BuildME v%s' % __version__
    # some more stuff?
    new_mi.to_excel(find_last_run().replace('.run', '_ODYM_mi.xlsx'), merge_cells=False)
    print("Wrote '%s'" % find_last_run().replace('.run', '_ODYM_mi.xlsx'))



def save_all_result_csv(res):
    res.to_csv(find_last_run().replace('.run', '_totals.csv'))


def calculate_measures(res):
    """
    Adds further metrics to the results collected in all_results_collector(), such as material and energy intensity,
    i.e. material / energy per floor area.
    :param res: Dataframe created by all_results_collector()
    :return: Dataframe with additional columns
    """
    return res


def all_results_collector(fnames):
    """
    Collects the results after the simulation.
    :return: Dictionary with scenario as key and material intensity, energy intensity, and e+ log file, e.g.
                {'USA_SFH_ZEB_RES0_1A_2015': {Asphalt_shingle: 4.2, ...}}
    """
    print("Collecting results...")
    ep_logs = collect_logs(fnames)
    material_res = load_material(fnames)
    energy_res = collect_energy(fnames)
    res = {}
    for f in ep_logs:
        res[f] = {**material_res[f], **energy_res[f], **ep_logs[f]}
    res = pd.DataFrame.from_dict(res, orient='index')
    res.index.names = ['scenario']
    save_all_result_csv(res)
    ei_result = save_ei_result(energy_res, material_res)
    save_ei_for_odym(ei_result)
    mi_result = save_mi_result(material_res)
    save_mi_for_odym(mi_result)


def cleanup():
    """
    Cleanes up temporary folders and files.
    :return:
    """
    pass


def create_sq_job(fnames):
    """
    ```
    rsync -ahvrPz
        /Users/n/code/BuildME/tmp/
        nh432@grace.hpc.yale.edu:/home/fas/hertwich/nh432/scratch60/190615/
    cp scratch60/190615/_run.txt ./run.txt
    module load Tools/SimpleQueue
    sqCreateScript -n 99 run.txt > run.sh
    sbatch run.sh
    rsync -avzhP --include="*/" --include="eplusout.csv" --include="*.err" --include="*.htm" --exclude="*"
        nh432@grace.hpc.yale.edu:/home/fas/hertwich/nh432/scratch60/190521/
        /Users/n/code/BuildME/tmp
    ```
    :param fnames:
    :return:
    """
    # https://docs.ycrc.yale.edu/clusters-at-yale/job-scheduling/simplequeue/
    initial_str = "source /apps/bin/try_new_modules.sh; module load EnergyPlus/9.1.0; module load gc; "
    run_file = os.path.join(settings.tmp_path, '_run.txt')
    with open(run_file, 'w') as run_file:
        for f in fnames:
            # TODO Change path below
            run_file.write(initial_str + "cd /home/fas/hertwich/nh432/scratch60/XXX/" + f + "; energyplus -r\n")



