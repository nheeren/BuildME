# BuildME

Framework to calculate building material & energy expenditures.

This model was used for the [UNEP IRP report on Ressource Efficiency](https://www.unenvironment.org/resources/report/resource-efficiency-and-climate-change-material-efficiency-strategies-low-carbon).
Please refer to this commit to reproduce the report results: https://github.com/nheeren/BuildME/commit/c164a0708ceef1aac632a22e585d0edb398e6bc6

## Setup

- Copy the [desired energyplus binaries](https://energyplus.net/downloads) to e.g. `./bin/EnergyPlus-9-2-0`
- Correct the paths in `BuildME/settings.py`

The current version should work on macOS, probably Linux, and will need some adaptations for Windows, such as renaming executable names, etc.



Copyright Niko Heeren, 2020
