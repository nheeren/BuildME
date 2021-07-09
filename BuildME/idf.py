"""
Functions to manipulate the IDF files.

Copyright: Niko Heeren, 2019
"""
import collections
import os

import pandas as pd
import numpy as np
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
            if s.Surface_Type != 'Window':
                if s.Outside_Boundary_Condition in boundary and s.Surface_Type in surface_type:
                    surfaces.append(s)
            else:
                if s.Outside_Boundary_Condition_Object in boundary and s.Surface_Type in surface_type:
                    surfaces.append(s)
    return surfaces


def extract_windows(idf):
    """
    Need a special function here, because eppy doesn't know the 'Window' object.
    If there are more use cases, this function can also be generlaized.
    :param idf:
    :return:
    """
    glazing = idf.idfobjects['Window'.upper()]
    windows = [SurrogateElement(g) for g in glazing]
    return windows


def extract_doors(idf):
    """
    Need a special function here, because eppy doesn't know the 'Door' object.
    If there are more use cases, this function can also be generlaized.
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


def get_surfaces(idf, energy_standard, res_scenario):
    """
    A function to derive all surfaces from the IDF file.
    Source: https://unmethours.com/question/15574/how-to-list-and-measure-area-surfaces/?answer=15604#post-id-15604
    The post also explains a method to calculate the external areas by orientation (not implemented here).
    :return: A dictionary for each surface type, e.g. {'ext_wall': [..., ...], 'roof': [...]}
    """
    surfaces = {}
    surfaces_to_count = ['Window', 'BuildingSurface:Detailed', 'Door']
    total_no_surfaces = [[s for s in idf.idfobjects[st.upper()]] for st in surfaces_to_count]
    # flatten the list
    total_no_surfaces = [item for sublist in total_no_surfaces for item in sublist]
    surfaces['ext_wall'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Outdoors'], ['Wall'])
    surfaces['int_wall'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Surface'], ['Wall'])
    surfaces['door'] = extract_doors(idf) + extract_surfaces(idf, ['FenestrationSurface:Detailed'], [''], ['Door'])
    surfaces['window'] = extract_windows(idf) + extract_surfaces(idf, ['FenestrationSurface:Detailed'], [''], ['Window'])
    surfaces['int_floor'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Adiabatic'], ['Floor']) + \
                                extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Surface'], ['Floor'])
    surfaces['int_ceiling'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Surface'], ['Ceiling'])
    surfaces['basement_ext_wall'] = extract_surfaces(idf, ['BuildingSurface:Detailed'],
                                                     ['GroundBasementPreprocessorAverageWall'], ['Wall'])
    surfaces['basement_int_floor'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Zone'], ['Floor'])
    surfaces['ext_floor'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Ground'], ['Floor']) + \
                            extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Outdoors'], ['Floor'])

    surfaces['ceiling_roof'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Zone'], ['Ceiling'])
    surfaces['roof'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Outdoors'], ['Roof'])
    check = [s.Name for s in total_no_surfaces if s.Name not in [n.Name for n in flatten_surfaces(surfaces)]]
    assert len(check) == 0, "Following elements were not found: %s" % check
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
    return surfaces

def extract_surfaces_zone_multiplier(list_surfaces, element_type, boundary, surface_type):
    """
    Function to extract the surfaces if a zone multiplier is used. Can't use the idf file and need to use a list
    of surfaces instead.
    :param list_surfaces: list of all surfaces
    :param element_type: BuildingSurface:Detailed or FenestrationSurface:Detailed
    :param boundary: Outdoors, Grounds etc.
    :param surface_type: Wall, Window etc.
    """
    surfaces = []
    for e in element_type:
        for s in list_surfaces:
            if s.Surface_Type != 'Window':
                if s.Outside_Boundary_Condition in boundary and s.Surface_Type in surface_type:
                    surfaces.append(s)
            else:
                if s.Outside_Boundary_Condition_Object in boundary and s.Surface_Type in surface_type:
                    surfaces.append(s)
    return surfaces

def get_surfaces_with_zone_multiplier(idf, energy_standard, res_scenario):
    """
    Function to extract surfaces for RT, as zone multiplier is used and windows are modeled in the FenestrationSurface:Detailed object.
    :param idf: The IDF file
    :param energy_standard:
    :param res_scenario:
    :return: list of surfaces accounting for zone multipliers
    """
    surfaces = {}

    surfaces_to_count = ['FenestrationSurface:Detailed', 'BuildingSurface:Detailed']

    # Extracting all surfaces from idf file
    surfaces_idf = [[s for s in idf.idfobjects[st.upper()]] for st in surfaces_to_count]

    # Flatten list
    surfaces_idf = [item for sublist in surfaces_idf for item in sublist]

    # Finding the multiplier used
    list_of_multipliers = [x.Multiplier for x in idf.idfobjects["ZONE"] if x.Multiplier is not '']
    zones_multipliers = [x.Name for x in idf.idfobjects["ZONE"] if x.Multiplier is not '']
    multipliers = dict(zip(zones_multipliers,list_of_multipliers))

    # Need to account for zone multiplier
    surfaces['ext_wall'] = extract_surfaces(idf, ['BuildingSurface:Detailed'],
                                                            ['Outdoors'], ['Wall'])
    surfaces['int_wall'] = extract_surfaces(idf, ['BuildingSurface:Detailed'],
                                                            ['Surface'], ['Wall'])
    surfaces['window'] = extract_surfaces(idf, ['FenestrationSurface:Detailed'], [''],
                                                          ['Window'])
    surfaces['int_floor'] = extract_surfaces(idf, ['BuildingSurface:Detailed'],
                                                             ['Adiabatic'], ['Floor']) + \
                            extract_surfaces(idf, ['BuildingSurface:Detailed'],
                                                             ['Surface'], ['Floor'])
    surfaces['int_ceiling'] = extract_surfaces(idf, ['BuildingSurface:Detailed'],
                                                               ['Surface'], ['Ceiling']) + \
                              extract_surfaces(idf, ['BuildingSurface:Detailed'],
                                                               ['Adiabatic'], ['Ceiling'])
    surfaces['ext_floor'] = extract_surfaces(idf, ['BuildingSurface:Detailed'],
                                                             ['Ground'], ['Floor']) + \
                            extract_surfaces(idf, ['BuildingSurface:Detailed'],
                                                             ['Outdoors'], ['Floor'])
    surfaces['roof'] = extract_surfaces(idf, ['BuildingSurface:Detailed'], ['Outdoors'],
                                                        ['Roof'])

    for key in surfaces.keys():
        temp_elem = []
        for elem in surfaces[key]:
            if elem.Surface_Type == 'Window':
                surface_name = elem.Building_Surface_Name
                for ext_wall_surface in surfaces['ext_wall']:
                    if ext_wall_surface.Name == surface_name:
                        zone_name = ext_wall_surface.Zone_Name
            else:
                zone_name = elem.Zone_Name

            if zone_name in multipliers.keys():
                temp_elem.extend(np.repeat(elem, multipliers[zone_name] - 1).tolist())
        surfaces[key].extend(temp_elem)

    temp_surface_areas = calc_surface_areas(surfaces)
    constr_list = {m.Name: m for m in read_constructions(idf)}
    slab_constr = constr_list['Surrogate_slab-' + res_scenario].Name

    if res_scenario == 'RES2.1' or res_scenario == 'RES2.1+RES2.2':
        floor_slab_constr = constr_list['Concrete_floor_slab-' + res_scenario].Name
        surfaces['int_floor_second_floor'] = create_surrogate_slab(temp_surface_areas['footprint_area'], floor_slab_constr)
        surfaces['basement'] = create_surrogate_basement(temp_surface_areas['footprint_area'], slab_constr)
        surfaces['slab'] = create_surrogate_slab(temp_surface_areas['footprint_area'], slab_constr)
        surfaces['basement1'] = create_surrogate_basement(temp_surface_areas['footprint_area'], slab_constr)
        surfaces['slab1'] = create_surrogate_slab(temp_surface_areas['footprint_area'], slab_constr)
    else:
        surfaces['basement'] = create_surrogate_basement(temp_surface_areas['footprint_area'], slab_constr)
        surfaces['basement1'] = create_surrogate_basement(temp_surface_areas['footprint_area'], slab_constr)
        surfaces['slab'] = create_surrogate_slab(temp_surface_areas['footprint_area'], slab_constr)
        surfaces['slab1'] = create_surrogate_slab(temp_surface_areas['footprint_area'], slab_constr)

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
                  'WindowMaterial:SimpleGlazingSystem', 'WindowMaterial:Blind',
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
    TODO: Not sure if this can be derived from the IDF file only.
    :return:
    """
    densities = {}
    for mat in materials_dict:
        # Some materials, such as Material:No Mass have no density attribute
        if hasattr(materials_dict[mat], 'Density'):
            densities[mat] = materials_dict[mat].Density
        else:
            # print(mat, materials_dict[mat].key)
            densities[mat] = fallback_mat.loc[mat, 'density']
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

