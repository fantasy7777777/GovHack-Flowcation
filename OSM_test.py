import osmnx as ox, networkx as nx
import matplotlib.pyplot as plt
from shapely.geometry import Point
import geopandas as gpd
import pandas as pd

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






# 1. Load the traffic light geojson
traffic_lights = gpd.read_file("Traffic_Lights.geojson")
# 2. Load your summarized CSV (peak/off-peak volumes)
volume_df = pd.read_csv("Traffic_Volumes_Summary.csv")
# 3. Make a lookup dictionary: {site_no: (offpeak, peak)}
volume_dict = volume_df.set_index("NB_SCATS_SITE")[["offpeak_volume", "peak_volume"]].to_dict("index")

for _, row in traffic_lights.iterrows():
    lon, lat = row['geometry'].x, row['geometry'].y
    nearest_node = ox.distance.nearest_nodes(G, lon, lat)
    G.nodes[nearest_node]['site_no'] = row['SITE_NO']
    
    vols = volume_dict.get(row['SITE_NO'])
    if vols:
        G.nodes[nearest_node]['offpeak_volume'] = vols["offpeak_volume"]
        G.nodes[nearest_node]["peak_volume"] = vols["peak_volume"]
    else:
        G.nodes[nearest_node]['offpeak_volume'] = 0
        G.nodes[nearest_node]['peak_volume'] = 0


for node, data in G.nodes(data=True):
    if "peak_volume" in data and data["peak_volume"] > 0:
        # Traffic-light-controlled intersection
        delay = min(120, data["peak_volume"] / 200.0)  # ~1 sec per 50 cars
    else:
        # Unsignalised intersection
        delay = 5  # base delay in seconds

    # Apply to all edges touching this node
    for u, v, k in G.in_edges(node, keys=True):
        G[u][v][k]['travel_time'] += delay
    for u, v, k in G.out_edges(node, keys=True):
        G[u][v][k]['travel_time'] += delay


cutoff = 60*8  # 20 minutes
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

target_site = 1044
highlight_node = None
for n, data in G.nodes(data=True):
    if data.get("site_no") == target_site:
        highlight_node = n
        break

if highlight_node is not None:
    hx, hy = G.nodes[highlight_node]["x"], G.nodes[highlight_node]["y"]
    ax.scatter(
        hx, hy,
        c="lime", s=200,
        edgecolors="black", linewidth=1.5,
        marker="*",
        zorder=6, label=f"Traffic Light {target_site}"
    )



plt.show()
