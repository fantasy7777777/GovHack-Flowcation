# GovHack

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This project is licensed under the MIT License.  
Feel free to fork, use, and modify it as per the license terms.

Read Me for 2025 GovHack for Flowcation project

DEPENDENCIES
- The packages used are listed in the requirements.txt file
- install the packages in a python environment by using the following terminal command:
    pip install -r requirements.txt

PROJECT OVERVIEW
- Goal: Calculate "travel rings" of locations of interest to visualise the catchment zone where the travel time for the given facilities are within the 20 minute neighbourhood goal
- Datasets: 
    This project uses Open Street Maps (OSM) which provided a graph data structure of anywhere in the world where edges are roads, railways, paths, etc and nodes are intersections of edges, such as traffic lights.
    This project uses Victoria Roads traffic signal data, inclusing the geographic coordinates of the lights and the volume of cars passing through each set of lights
    For demo purposes, we took the traffic volume for august 2025, split it into off-peak traffic (10am to 1pm) and peak traffic (3pm to 6pm).
    
- Method:
    This traffic volume data was mapped to nodes on the OSM graph with the same coordinates as the corresponding lights.
    Travel time delays based on the car volume were applied to simulate congestion
    Shortest path algorithms are applied to find all of the nodes within a 20 minute travel time "radius" of the locations of interest
    A boundary is rendered to demonstrate how far you can travel based on time

Generating Graphs
- In the interest of time, hard coded scripts were made for generating the travel rings for cars, bikes and pedestrians
- They have their respective files, "drive_graph.py", "bike_graph.py", and "walk_graph.py"
- You can edit the variables inside the file such as which building features to calculate the rings for, eg, library, hospital. Any tag which is available through the Open Street Maps Database can be used.
- It will download geojson files to a cache folder, form the graph, and then a matplotlib plot should pop up with the map of the location, red dots highlighting the locations of the facilities you filtered, and a blue blob centered around each red dot, which represents how far you can get within 20 minutes return


