"""
Settings and constants required for the model to run.

Copyright: Niko Heeren, 2019
"""

import os
import platform

ep_version = '9.2.0'
basepath = os.path.abspath('.')
ep_path = os.path.abspath("./bin/EnergyPlus-9-2-0/")
ep_idd = os.path.abspath("./bin/EnergyPlus-9-2-0/Energy+.idd")

# Checking OS and modify files to copy
if platform.system() == 'Windows':
    ep_exec_files = ["energyplus.exe", "Energy+.idd", "EPMacro.exe", "ExpandObjects.exe",
                     "PreProcess/GrndTempCalc/Basement.exe", "PreProcess/GrndTempCalc/BasementGHT.idd",
                     "PreProcess/GrndTempCalc/Slab.exe", "PreProcess/GrndTempCalc/SlabGHT.idd",
                     "PostProcess/ReadVarsESO.exe", "energyplusapi.dll"
                     ]
elif platform.system() == 'Darwin':
    ep_exec_files = ["energyplus", "energyplus-%s" % ep_version, "Energy+.idd", "EPMacro", "ExpandObjects",
                 "libenergyplusapi.%s.dylib" % ep_version,  # required by energyplus
                 "libgfortran.3.dylib", "libquadmath.0.dylib",  # required by ExpandObjects
                 "PreProcess/GrndTempCalc/Basement", "PreProcess/GrndTempCalc/BasementGHT.idd",
                 "PreProcess/GrndTempCalc/Slab", "PreProcess/GrndTempCalc/SlabGHT.idd",
                 "PostProcess/ReadVarsESO"
                 ]
else:
    print('OS is not supported!')

archetypes = os.path.abspath("./data/archetype/")
tmp_path = os.path.abspath("./tmp/")
climate_files_path = os.path.abspath("./data/climate/meteonorm71/")
shielding = 'medium'  # wind shielding, needed for MMV simulations; set to low, medium or high

# The combinations
#   Example: USA.SFH_standard.RES0.


debug_combinations = {
    'USA':
        {'occupation': ['MFH'],
         'energy standard': ['standard'],
         'RES': ['RES0'],
         'climate_region': ['1A'],
         'climate_scenario': ['2015'],
         'cooling': ['MMV']
         }
}

combinations = \
    {
        'USA':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['1A', '2A', '2B', '3A', '3B-Coast', '3B', '3C',
                  '4A', '4B', '4C',
                  '5A', '5B', '6A', '6B', '7', '8'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'DE':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['Germany'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'CN':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['I', 'II', 'III', 'IV', 'V'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'JP':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['JP1', 'JP2', 'JP3', 'JP4', 'JP5', 'JP6', 'JP7', 'JP8'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'IT':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['Italy'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'FR':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['France'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'PL':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['Poland'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'CA':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['CA5A', 'CA6A', 'CA7'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'R32EU12-M':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['R32EU12-M'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'IN':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['IN1', 'IN2', 'IN3', 'IN4', 'IN5'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'ES':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['Spain'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'UK':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['UK'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'Oth-R32EU15':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['Oth-R32EU15'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'Oth-R32EU12-H':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['Oth-R32EU12-H'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'Oth-Asia':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['Indonesia'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'Oth-LAM':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['Brazil'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'Oth-MAF':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['Egypt'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'Oth-MAF-Sub-Sahara':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['Nigeria'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'Oth-OECD':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['Turkey'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
        'Oth-REF':
            {'occupation': ['RT', 'MFH', 'SFH'],
             'energy standard': ['non-standard', 'standard', 'efficient', 'ZEB'],
             'RES': ['RES0', 'RES2.1', 'RES2.2', 'RES2.1+RES2.2'],
             'climate_region':
                 ['Russia'],
             'climate_scenario': ['2015'],
             'cooling': ['HVAC', 'MMV']
             },
    }


climate_stations = {
    'USA': {
        '1A': 'Miami_FL-hour.epw',
        '2A': 'Houston_Airp_TX-hour.epw',
        '2B': 'Phoenix_AZ-hour.epw',
        '3A': 'Atlanta_GA-hour.epw',
        '3B-Coast': 'Los_Angeles_CA-hour.epw',
        '3B': 'Las_Vegas_NV-hour.epw',
        '3C': 'San_Francisco_CA-hour.epw',
        '4A': 'Baltimore_MD-hour.epw',
        '4B': 'US-Albuquerque_NM-hour.epw',
        '4C': 'Seattle_Tacoma_WA-hour.epw',
        '5A': 'Chicago_IL-hour.epw',
        '5B': 'Boulder_CO-hour.epw',
        '6A': 'Minneapolis_Airp_MN-hour.epw',
        '6B': 'Helena_MT-hour.epw',
        '7': 'Duluth_Airp_MN-hour.epw',
        '8': 'Fairbanks_AK-hour.epw'},
    'DE': {'Germany': 'Frankfurt_am_Main_Airp_-hour.epw'},
    'CN': {'I': 'CN-Harbin.epw',
           'II': 'CN-Beijing.epw',
           'III': 'CN-Wuhan.epw',
           'IV': 'CN-Haikou.epw',
           'V': 'CN-Kunming.epw'},
    'JP': {
        'JP1': 'JP-Asahikawa-hour.epw',
        'JP2': 'JP-Sapporo-hour.epw',
        'JP3': 'JP-Morioka-hour.epw',
        'JP4': 'JP-Sendai-hour.epw',
        'JP5': 'JP-Tsukuba_JA-hour.epw',
        'JP6': 'JP-Osaka-hour.epw',
        'JP7': 'JP-Miyazaki-hour.epw',
        'JP8': 'JP-Naha-hour.epw'},
    'IT': {'Italy': 'Roma_Ciampino-hour.epw'},
    'FR': {'France': 'PARIS_FR-hour.epw'},
    'PL': {'Poland': 'PL-Warszawa-hour.epw'},
    'CA': {'CA5A': 'Chicago_IL-hour.epw',
           'CA6A': 'Minneapolis_Airp_MN-hour.epw',
           'CA7': 'Duluth_Airp_MN-hour.epw'},
    'R32EU12-M': {'R32EU12-M': 'PL-Warszawa-hour.epw'},
    'IN': {
        'IN1': 'IN-Jodhpur.epw',
        'IN2': 'IN-Santacruz_Bombay.epw',
        'IN3': 'IN-Bangalore.epw',
        'IN4': 'IN-Shimla.epw',
        'IN5': 'IN-Hyderabad.epw'},
    'ES': {'Spain': 'Madrid_Barajas-hour.epw'},
    'UK': {'UK': 'Aughton-hour.epw'},
    'Oth-R32EU15': {'Oth-R32EU15': 'PL-Warszawa-hour.epw'},
    'Oth-R32EU12-H': {'Oth-R32EU12-H': 'PL-Warszawa-hour.epw'},
    'Oth-OECD': {'Turkey': 'Istanbul_TU-hour.epw'},
    'Oth-REF': {'Russia': 'MOSKVA_RS-hour.epw'},
    'Oth-Asia': {'Indonesia': 'JAKARTA_ID-hour.epw'},
    'Oth-MAF': {'Egypt': 'CAIRO_EG-hour.epw'},
    'Oth-MAF-Sub-Sahara': {'Nigeria': 'BENIN_NI-hour.epw'},
    'Oth-LAM': {'Brazil': 'Rio_de_Janeiro_BR-hour.epw'}
}

odym_materials = odym_materials = {'Asphalt_shingle': 'other',
                  'Air_4_in_vert': 'other',
                  'Bldg_paper_felt': 'paper and cardboard',
                  'Std Wood 6inch': 'wood and wood products',
                  'Std Wood 10cm': 'wood and wood products',
                  'Lumber_2x4': 'wood and wood products',
                  'OSB_1/2in': 'wood and wood products',
                  'OSB_5/8in': 'wood and wood products',
                  'Stucco_1in': 'cement',
                  'F07 25mm stucco': 'cement',
                  'F07 50mm stucco': 'cement',
                  'F07 10mm stucco': 'cement',
                  'Concrete_tiles_25mm': 'concrete',
                  'Bitumen_20mm': 'other',
                  'sheathing_consol_layer': 'wood and wood products',
                  'Drywall_1/2in': 'wood and wood products',
                  'G01 16mm gypsum board': 'other',
                  'G01 13mm gypsum board': 'other',
                  'ceil_consol_layer-en-non-standard': 'other',
                  'ceil_consol_layer-en-standard': 'other',
                  'ceil_consol_layer-en-efficient': 'other',
                  'ceil_consol_layer-en-ZEB': 'other',
                  'door_const': 'wood and wood products',
                  'Glass-en-non-standard': 'other',
                  'Glass-en-standard': 'other',
                  'Glass-en-efficient': 'other',
                  'Glass-en-ZEB': 'other',
                  'Plywood_3/4in': 'wood and wood products',
                  'Carpet_n_pad': 'other',
                  'floor_consol_layer': 'wood and wood products',
                  'Concrete_20cm': 'concrete',
                  'Reinforcement_1perc_20cm': 'construction grade steel',
                  'Concrete_15cm': 'concrete',
                  'Reinforcement_1perc_15cm': 'construction grade steel',
                  'Concrete_12cm': 'concrete',
                  '100mm Normalweight concrete floor': 'concrete',
                  '175mm Normalweight concrete floor': 'concrete',
                  '200mm Normalweight concrete floor': 'concrete',
                  'Reinforcement_1perc_12cm': 'construction grade steel',
                  'wall_consol_layer-en-non-standard': 'other',
                  'wall_consol_layer-en-standard': 'other',
                  'wall_consol_layer-en-efficient': 'other',
                  'wall_consol_layer-en-ZEB': 'other',
                  'F13 Built-up roofing': 'other',
                  'F08 Metal surface': 'other',
                  'Reinforcement_2perc_15cm': 'construction grade steel',
                  'Reinforcement_3perc_15cm': 'construction grade steel',
                  'Reinforcement_2perc_20cm': 'construction grade steel',
                  'Reinforcement_2perc_30cm': 'construction grade steel',
                  'Concrete_30cm': 'concrete',
                  'Concrete_10cm': 'concrete',
                  'Reinforcement_1perc_10cm': 'construction grade steel',
                  'Concrete_18cm': 'concrete',
                  'Reinforcement_2perc_17cm': 'construction grade steel',
                  'CLT_170mm': 'wood and wood products',
                  'Concrete_60cm': 'concrete',
                  'Reinforcement_1perc_60cm': 'construction grade steel',
                  'High pressure laminate panel': 'other',
                  'Concrete_4cm': 'concrete',
                  'Concrete_5cm': 'concrete',
                  'Concrete_7cm': 'concrete',
                  'Reinforcement_1perc_7cm': 'construction grade steel',
                  'Cement_plaster_0.012': 'cement',
                  'Brick - fired clay - 1920 kg/m3 - 200mm': 'brick',
                  'Brick - fired clay - 1920 kg/m3 - 300mm': 'brick',
                  'Brick - fired clay - 1600 kg/m3 - 102mm': 'brick',
                  'Brick - fired clay - 1600 kg/m3 - 230mm': 'brick',
                  'Metal_surface': 'other'}

odym_regions = {'USA': 'R32USA',
                'CA': 'R32CAN',
                'CN': 'R32CHN',
                'R32EU12-M': 'R32EU12-M',
                'IN': 'R32IND',
                'JP': 'R32JPN',
                'FR': 'France',
                'DE': 'Germany',
                'IT': 'Italy',
                'PL': 'Poland',
                'ES': 'Spain',
                'UK': 'UK',
                'Oth-R32EU15': 'Oth-R32EU15',
                'Oth-R32EU12-H': 'Oth-R32EU12-H',
                'Oth-OECD': 'R5.2OECD_Other',
                'Oth-REF': 'R5.2REF_Other',
                'Oth-Asia': 'R5.2ASIA_Other',
                'Oth-MAF-Sub-Sahara': 'R5.2MAF_Other_Sub_Sahara',
                'Oth-MAF': 'R5.2MAF_Other',
                'Oth-LAM': 'R5.2LAM_Other'}
