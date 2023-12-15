
# ME Memory Organizator

Scripts for generating SRAM memory organizations for store the Search Area and the Current Block of a ME System. 
Each memory organization are simulated with cacti to evaluate area requirements and power consumption.

## Files
main.py
Contains the main functions for generating the SRAM organizations

functions.py
Contains the functions to run the cacti software, as generating the .cfg file, run simulation and catch results.

## Running:
Compile cacti:

    cd cacti/
    make

Run main.py
  
    python3 main.py
