"""
Functions to manipulate the IDF files.

Copyright: Niko Heeren, 2019
"""
import collections
import os
import math
import pandas as pd
import numpy as np
import logging
from eppy.modeleditor import IDF

from BuildME import settings

class SurrogateElement:
    """
    A surrogate class for windows and doors, because e.g. idf.idfobjects['Window'.upper()] does not contain an 'area'
    attribute. See also https://github.com/santoshphilip/eppy/issues/230.
    """
    def __init__(self, g):
        if type(g) == dict:
            self.area = g['area']
            self.Building_Surface_Name = g['Building_Surface_Name']
            self.Construction_Name = g['Construction_Name']
            self.key = g['key']
            self.Name = g['Name']
        else:
            self.area = g.Length * g.Height
            self.Building_Surface_Name = g.Building_Surface_Name
            self.Construction_Name = g.Construction_Name
            self.key = g.key
            self.Name = g.Name
            # self.Outside_Boundary_Condition = g.Outside_Boundary_Condition
            # self.Zone_Name = g.Zone_Name
            # self.Surface_Type = g.Surface_Type


class SurrogateMaterial:
    # TODO: DELETE?
    """
    A surrogate class for materials, such as, because some material types (e.g. 'Material:NoMass') do not contain
    certain attributes that are later required (e.g. 'Density').
    """
    def __init__(self, g):
        self.key = g.key
        self.Name = g.Name
        self.Density = None


def extract_surfaces(idf, element_type, boundary, surface_type):
    """
    Fetches the elements from an IDF file and returns them in a list.
    :param idf: The IDF file
    :param element_type: The elements to be considered, e.g. ['BuildingSurface:Detailed', 'Window']
    :param boundary: "!- Outside Boundary Condition" as specified in the IDF, e.g. ['Outdoors']
    :param surface_type: "!- Surface Type" as specified in the IDF file, e.g. ['Wall']
    :return: List of eppy elements
    """
    surfaces = []
    for e in element_type:
        for s in idf.idfobjects[e.upper()]:
            #Some door objects also can be modeled with outside boundary condition object
            if s.Surface_Type != 'Window' and s.Surface_Type != 'Door' and s.Surface_Type != 'GlassDoor':
                if s.Outside_Boundary_Condition in boundary and s.Surface_Type in surface_type:
                    surfaces.append(s)
            else:
                if s.Outside_Boundary_Condition_Object in boundary and s.Surface_Type in surface_type:
                    surfaces.append(s)
    return surfaces


def extract_windows(idf):
    """
    Need a special function here, because eppy doesn't know the 'Window' object.
    If there are more use cases, this function can also be generalized.
    :param idf:
    :return:
    """
    glazing = idf.idfobjects['Window'.upper()]
    windows = [SurrogateElement(g) for g in glazing]
    return windows


def extract_doors(idf):
    """
    Need a special function here, because eppy doesn't know the 'Door' object.
    If there are more use cases, this function can also be generalized.
    :param idf:
    :return:
    """
    doors = idf.idfobjects['Door'.upper()]
    windows = [SurrogateElement(d) for d in doors]
    return windows


def flatten_surfaces(surfaces):
    """
    Just a simple function to flatten the surfaces dictionary created in get_surfaces() and return it as a list.
    :param surfaces: dictionary created by get_surfaces()
    :return: flat list of elements e.g. [BuildingSurface:Detailed,...]
    """
    flat = [[s for s in surfaces[sname]] for sname in surfaces]
    flat = [item for sublist in flat for item in sublist]
    return flat


def read_idf(in_file):
    # in_file = os.path.join(filepath, filename)
    idd = settings.ep_idd
    IDF.setiddname(idd)
    with open(in_file, 'r') as infile:
        idf = IDF(infile)
    return idf


def get_surfaces(idf, energy_standard, res_scenario, archetype):
    """
    A function to derive all surfaces from the IDF file.

    Source: https://unmethours.com/question/15574/how-to-list-and-measure-area-surfaces/?answer=15604#post-id-15604
    NB: The post also explains a method to calculate the external areas by orientation (not implemented here).
    :return: A dictionary for each surface type, e.g. {'ext_wall': [..., ...], 'roof': [...]}
    """
    surfaces = {}
    surfaces_to_count = ['Window', 'BuildingSurface:Detailed', 'Door', 'FenestrationSurface:Detailed']
    # Extracting all surfaces from idf file
    total_no_surfaces = [[s for s in idf.idfobjects[st.upper()]] for st in surfaces_to_count]
    # flatten the list
    total_no_surfaces = [item for sublist in total_no_surfaces for item in sublist]

    surfaces['ext_wall'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Outdoors'], ['Wall'])
    surfaces['int_wall'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Surface'], ['Wall']) + \
                           extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Zone'], ['Wall'])
    surfaces['door'] = extract_doors(idf) + extract_surfaces(idf, ['FenestrationSurface:Detailed'], [''], ['Door'])
    surfaces['window'] = extract_windows(idf) + extract_surfaces(idf, ['FenestrationSurface:Detailed'], [''], ['Window']) + \
                         extract_surfaces(idf, ['FenestrationSurface:Detailed'], [''], ['GlassDoor'])
    surfaces['int_floor'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Surface'], ['Floor'])
    surfaces['int_ceiling'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Surface'], ['Ceiling']) + \
                              extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Adiabatic'], ['Ceiling'])
    surfaces['basement_ext_wall'] = extract_surfaces(idf, ['BuildingSurface:Detailed'],
                                                     ['GroundBasementPreprocessorAverageWall'], ['Wall']) + \
                                    extract_surfaces(idf, ['BuildingSurface:Detailed'],
                                                     ['GroundFCfactorMethod'], ['Wall'])
    surfaces['basement_int_floor'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Zone'], ['Floor'])
    surfaces['ext_floor'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Adiabatic'], ['Floor']) + \
                            extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Ground'], ['Floor']) + \
                            extract_surfaces(idf, ['BuildingSurface:Detailed'], ['GroundSlabPreprocessorAverage'],
                                             ['Floor']) + \
                            extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Outdoors'], ['Floor']) + \
                            extract_surfaces(idf, ['BuildingSurface:Detailed'], ['GroundFCfactorMethod'], ['Floor'])
    surfaces['ceiling_roof'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Zone'], ['Ceiling'])
    surfaces['roof'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Outdoors'], ['Roof'])
    # Check what surfaces are present in `total_no_surfaces` but were missed in `surfaces`
    check = [s.Name for s in total_no_surfaces if s.Name not in [n.Name for n in flatten_surfaces(surfaces)]]
    assert len(check) == 0, "Following elements are not accounted for: %s" % check

    multipliers = {x.Name: int(float(x.Multiplier)) for x in idf.idfobjects["ZONE"] if x.Multiplier is not ''}

    for key in surfaces.keys():
        temp_elem = []
        for elem in surfaces[key]:
            if key in ['door', 'window']:
                surface_name = elem.Building_Surface_Name
                zone_name = [obj.Zone_Name for obj in idf.idfobjects['BuildingSurface:Detailed'] if obj.Name == surface_name]
                zone_name = zone_name[0]  # the window should belong to exactly one wall
            else:
                zone_name = elem.Zone_Name

            if zone_name in multipliers.keys():
                temp_elem.extend(np.repeat(elem, multipliers[zone_name] - 1).tolist())
        surfaces[key].extend(temp_elem)

    temp_surface_areas = calc_surface_areas(surfaces)
    constr_list = {m.Name: m for m in read_constructions(idf)}
    if 'attic-ceiling-' + energy_standard in [x for x in constr_list]:
        print('adding interior walls... ')
        int_wall_constr = constr_list['attic-ceiling-' + energy_standard].Name
        surfaces['int_wall'] = surfaces['int_wall'] +\
                           (create_surrogate_int_walls(temp_surface_areas['floor_area_wo_basement'], int_wall_constr))
    if 'Surrogate_slab-' + res_scenario in [x for x in constr_list]:
        print('adding basement... ')
        slab_constr = constr_list['Surrogate_slab-' + res_scenario].Name
        surfaces['slab'] = create_surrogate_slab(temp_surface_areas['footprint_area'], slab_constr)
        surfaces['basement'] = create_surrogate_basement(temp_surface_areas['footprint_area'], slab_constr)

    if archetype in ['Office', 'RT']:
        # Do not have to add surrogate internal walls as those are added already in the idf file, but shear walls
        shear_constr = constr_list['Shear_wall-' + res_scenario].Name
        surfaces['shear_wall'] = create_surrogate_shear_wall(temp_surface_areas['floor_area_wo_basement'], shear_constr)
    return surfaces


def create_surrogate_int_walls(floor_area, construction, linear_m=0.4, room_h=2.8):
    """
    Since IDF files sometimes do not contain internal walls, this function will create surrogate internal walls.
    Based on Kellenberger et al. 2012, 0.4 m per 1.0 m2 floor area is assumed. Assuming a room height of 2.8 m,
     this corresponds to  1.12 m2 per 1.0 m2 floor area.
    :return: List of one surface which can be added to the surfaces variable in get_surfaces().
    """
    int_wall = {
        'key': 'DummyBuildingSurface',
        'Name': 'surrogate_int_wall',
        'Building_Surface_Name': None,
        'Construction_Name': construction,
        'area': linear_m * floor_area * room_h
    }
    return [SurrogateElement(int_wall)]


def create_surrogate_slab(floor_area, construction):
    slab = {
        'key': 'DummyBuildingSurface',
        'Name': 'surrogate_slab',
        'Building_Surface_Name': None,
        'Construction_Name': construction,
        'area': floor_area
    }
    return [SurrogateElement(slab)]


def create_surrogate_basement(floor_area, construction, room_h=2.8):
    basem = {
        'key': 'DummyBuildingSurface',
        'Name': 'surrogate_basement',
        'Building_Surface_Name': None,
        'Construction_Name': construction,
        # assuming a square floor layout
        'area': floor_area ** 0.5 * 4 * room_h
    }
    return [SurrogateElement(basem)]


def create_surrogate_shear_wall(floor_area, construction):
    """
    The RT archetype need shear/core walls for lateral load resistance.
    Based on Taranath: Reinforced Concrete Design of Tall Buildings p. 144: 0.08 m per 1.0 m2 floor area is assumed.
    Assuming room height of 3 m, this yields 0.24 m2 per m2 floor area.

    :return: List of one surface which can be added to the surfaces variable in get_surfaces().
    """
    shear_walls = {
        'key': 'DummyBuildingSurface',
        'Name': 'surrogate_shear_wall',
        'Building_Surface_Name': None,
        'Construction_Name': construction,
        'area': 0.24*floor_area
    }
    return [SurrogateElement(shear_walls)]


def calc_surface_areas(surfaces, floor_area=['int_floor', 'ext_floor']):
    """
    Sums the surfaces as created by get_surfaces() and returns a corresponding dict.
    :param floor_area:
    :param surfaces:
    :return:
    """
    areas = {}
    for element in surfaces:
        areas[element] = sum(e.area for e in surfaces[element])
    areas['ext_wall_area_net'] = areas['ext_wall'] - areas['window']
    areas['floor_area_wo_basement'] = sum([areas[s] for s in areas if s in floor_area])
    areas['footprint_area'] = areas['ext_floor']
    return areas


def calc_envelope(areas):
    """
    Calculates the total envelope surface area in the surfaces variable created by get_surfaces().
    :param areas:
    :return: Dictionary of surface area with and without basement
    """
    envelope = {
        'envelope_w_basement': sum(areas[s] for s in ['ext_wall', 'roof', 'ext_floor']),
        'envelope_wo_basement': areas['envelope_w_basement'] + areas['basement_ext_wall']}
    return envelope


def read_materials(idf):
    materials = []
    for mtype in ['Material', 'Material:NoMass', 'Material:AirGap',
                  'WindowMaterial:SimpleGlazingSystem', 'WindowMaterial:Blind','WindowMaterial:Shade',
                  'WindowMaterial:Glazing']:
        materials = materials + [i for i in idf.idfobjects[mtype.upper()]]
    find_duplicates(materials)
    # TODO: Will need to think about windows...
    return materials


def load_material_data():
    filedata = pd.read_excel('data/material.xlsx', sheet_name='properties', index_col='ep_name')
    return filedata


def find_duplicates(idf_object, crash=True):
    """
    Checks if duplicate entries in an IDF object exist
    :param crash:
    :param idf_object:
    :return: None
    """
    object_names = [io.Name for io in idf_object]
    duplicates = [item for item, count in collections.Counter(object_names).items() if count > 1]
    if crash:
        assert len(duplicates) == 0, "Duplicate entries for IDF object: '%s'" % duplicates
    else:
        return duplicates


def make_materials_dict(materials):
    """
    Takes the eppy materials objects and places them into a dictionary with the .Name attribute as the key,
    e.g. {material.Name: material}
    :param materials: list of eppy idf objects as created by read_materials()
    :return: dictionary with the .Name attribute as the key {material.Name: material}
    """
    # Making sure there are no duplicate Material entries in the IDF file
    materials_dict = {m.Name: m for m in materials}
    return materials_dict


def make_mat_density_dict(materials_dict, fallback_mat):
    """
    Creates a dictionary of material densities by material.
    :param materials_dict: Materials from the IDF file
    :param fallback_mat: Data drom 'data/materials.xlsx'
    :return:
    """
    densities = {}
    oopsies = []
    for mat in materials_dict:
        # Some materials, such as Material:No Mass have no density attribute
        if hasattr(materials_dict[mat], 'Density'):
            densities[mat] = materials_dict[mat].Density
        elif mat in fallback_mat.index:
            densities[mat] = fallback_mat.loc[mat, 'density']
        else:
            # print(mat, materials_dict[mat].key)
            oopsies.append(mat)
    if len(oopsies) != 0:
        df = pd.DataFrame(oopsies)
        df.to_csv('data/material_candidates.csv', index=False, header=False)
        raise AssertionError("%i materials have no density defined in idf Constructions nor in data/materials.xlsx: %s."
                             "\nSee also 'data/material_candidates.csv' dump."
                             % (len(oopsies), oopsies))
    return densities


def read_constructions(idf):
    """
    Gets the "Construction" elements from the idf files.
    :param idf:
    :return:
    """
    constructions = idf.idfobjects['Construction'.upper()]
    find_duplicates(constructions)
    return constructions


def extract_layers(construction):
    res = {}
    layers = ['Outside_Layer'] + ['Layer_'+str(i+2) for i in range(9)]
    for l in layers:
        if getattr(construction, l) == '':
            break  # first empty value found
        res[l] = getattr(construction, l)
    return res


def get_fenestration_objects_from_surface(idf, surface_obj):
    """
    Finds all fenestration objects assigned to a given surface
    :param idf: The .idf file
    :param surface_obj: Surface object (BuildingSurface:Detailed)
    :return: list of fenestration objects
    """
    surface = surface_obj.Name
    fenestration = []
    for item in ['Window', 'Door', 'FenestrationSurface:Detailed']:
        new = [obj for obj in idf.idfobjects[item] if obj.Building_Surface_Name == surface]
        fenestration.extend(new)
    return fenestration


def add_ground_floor_ffactor(mat_vol, obj, area, densities):
    """
    Adds ground floor material layers (concrete and insulation) based on the Ffactor method
    https://bigladdersoftware.com/epx/docs/8-7/engineering-reference/ground-heat-transfer-calculations-using-c.html
    + Table A6.3 Assembly F-Factors for Slab-on-Grade Floors from ASHRAE Energy standard for buildings except low rise residential buildings
    (we assume 48 inch=1.22m vertical footing+insulation)
    :param mat_vol: A dictionary with materials and their respective volumes
    :return: the dictionary including Ffactor materials
    """
    res = (obj.Name).split('-')[-1]
    if res == 'RES0':
        multiplier = 1
    elif res in ('RES2.2', 'RES2.1+RES2.2'):
        multiplier = 0.8
    else:
        print(f'Warning: The RES type {res} was not recognized / implemented...')
        multiplier = 1.0
    material = 'Concrete'
    densities[material] = 2200
    # 15 cm layer of concrete of the floor (20% less for RES other than RES0)
    if material not in mat_vol:
        mat_vol[material] = 0.15*obj.Area*multiplier
    else:
        mat_vol[material] += 0.15*obj.Area*multiplier
    # 15 cm layer of concrete of the footing (20% less for RES other than RES0)
    mat_vol[material] += 0.15*1.22*obj.PerimeterExposed*multiplier
    material = 'Insulation'  # fictious layer of insulation
    densities[material] = 120
    ffactor = obj.FFactor
    # we derive an exponential regression line from Ffactor and insulation xsection (m2, height x thickness)
    # based on ASHRAE Table A6.3, assuming conductivity of 0.036 W/m-K for converting R-values to insulation thickness
    if 0.4<ffactor<0.65: # case for unheated slab, fit R^2 = 0.90
        xsection = 93.732*math.exp(-14.25*ffactor)
    elif 0.65<ffactor<1.1: # case for heated slab, fit R^2 = 0.90
        xsection = 20.806*math.exp(-6.82*ffactor)
    else:
        logging.warning(f'The F-factor of the object {obj.Name} has a value outside of the known range. The insulation layer is skipped.')
        xsection = 0 # we don't have ASHRAE values for these cases, skip insulation
    if material not in mat_vol:
        mat_vol[material] = xsection*obj.PerimeterExposed
    else:
        mat_vol[material] += xsection*obj.PerimeterExposed
    return mat_vol, densities


def add_underground_wall_cfactor(mat_vol, obj, area, densities):
    """
    Adds underground wall material layers (concrete and insulation) based on the Cfactor method
    https://bigladdersoftware.com/epx/docs/8-7/engineering-reference/ground-heat-transfer-calculations-using-c.html
    :param mat_vol: A dictionary with materials and their respective volumes
    :return: the dictionary including Cfactor materials
    """
    res = (obj.Name).split('-')[-1]
    if res == 'RES0':
        multiplier = 1
    elif res in ('RES2.2', 'RES2.1+RES2.2'):
        multiplier = 0.8
    else:
        print(f'Warning: The RES type {res} was not recognized / implemented...')
        multiplier = 1.0
    material = 'Concrete'
    densities[material] = 2200
    # 15 cm layer of concrete of the floor (20% less for RES other than RES0)
    if material not in mat_vol:
        mat_vol[material] = 0.15*area*multiplier
    else:
        mat_vol[material] += 0.15*area*multiplier
    material = 'Insulation' # fictious layer of insulation
    densities[material] = 120
    thickness = (1/obj.CFactor+0.0607+0.3479*obj.Height-0.15/1.95)*0.036
    if material not in mat_vol:
        mat_vol[material] = thickness*area
    else:
        mat_vol[material] += thickness*area
    return mat_vol, densities