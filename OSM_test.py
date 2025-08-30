import osmnx as ox, networkx as nx
import matplotlib.pyplot as plt
from shapely.geometry import Point
import geopandas as gpd

ox.settings.cache_folder = "cache_parkville"
places = [
    "Parkville, Victoria, Australia",
    "Carlton, Victoria, Australia",
    "Fitzroy, Victoria, Australia",
    "North Melbourne, Victoria, Australia"
]
address = "University High School, Parkville, Victoria, Australia"

G = ox.graph_from_place(places, network_type="drive")

nodes, edges = ox.graph_to_gdfs(G)
school = ox.geocode(address)

default_speeds = {
    "motorway": 100,
    "trunk": 80,
    "primary": 60,
    "secondary": 50,
    "tertiary": 50,
    "residential": 40,
    "service": 20
}

ox.routing.add_edge_speeds(G, hwy_speeds=default_speeds, fallback=40)
ox.routing.add_edge_travel_times(G)

lat, lon = -37.7969983, 144.954471
school_node = ox.distance.nearest_nodes(G, lon, lat)

# Query for schools
tags = {"amenity": "school"}
schools = ox.features_from_place(places, tags=tags)

node_id = ox.distance.nearest_nodes(G, school[1], school[0])  # X=lon, Y=lat


cutoff = 60  # 20 minutes
lengths = nx.single_source_dijkstra_path_length(G, school_node, cutoff=cutoff, weight="travel_time")
reachable_nodes = list(lengths.keys())

# Make a GeoDataFrame of the reachable nodes
points = [Point((G.nodes[n]["x"], G.nodes[n]["y"])) for n in reachable_nodes]
gdf = gpd.GeoDataFrame(geometry=points, crs="EPSG:4326")

# Project to meters before geometric ops
gdf_proj = gdf.to_crs(epsg=32755)  # UTM zone for Melbourne

# Compute convex hull
hull = gdf_proj.unary_union.convex_hull
hull_gdf = gpd.GeoDataFrame(geometry=[hull], crs=gdf_proj.crs)

# Reproject back to WGS84 for overlay
hull_gdf = hull_gdf.to_crs(epsg=4326)


#plotting
fig, ax = ox.plot_graph(
    G,
    node_size=10,
    node_color="grey",
    node_zorder=1,
    edge_color="lightgrey",
    show=False,
    close=False
)

# highlight schools
schools_centroids = schools.centroid
schools_centroids.plot(ax=ax, color="red", markersize=50, label="Schools")

x = [G.nodes[n]["x"] for n in reachable_nodes]
y = [G.nodes[n]["y"] for n in reachable_nodes]
ax.scatter(x, y, c="yellow", s=15, label="<=20 min")

x, y = G.nodes[school_node]["x"], G.nodes[school_node]["y"]
ax.scatter(x, y,
           c="green", s=120,
           edgecolors="white", linewidth=1.2,
           zorder=5, label="School")

# Plot

hull_gdf.boundary.plot(ax=ax, color="orange", linewidth=2)

plt.show()








