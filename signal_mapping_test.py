import osmnx as ox
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

# Load graph
ox.settings.cache_folder = "cache_parkville"
places = [
    "Parkville, Victoria, Australia",
    "Carlton, Victoria, Australia",
    "Fitzroy, Victoria, Australia",
    "North Melbourne, Victoria, Australia"
]
G = ox.graph_from_place(places, network_type="drive")

# Load traffic lights
traffic_lights = gpd.read_file("Traffic_Lights.geojson")

# Store results
records = []

for _, row in traffic_lights.iterrows():
    lon, lat = row.geometry.x, row.geometry.y
    site_no = row["SITE_NO"]

    # Find nearest node in graph
    nearest_node = ox.distance.nearest_nodes(G, lon, lat)

    # Save mapping
    records.append({
        "SITE_NO": site_no,
        "node_id": nearest_node,
        "node_lon": G.nodes[nearest_node]["x"],
        "node_lat": G.nodes[nearest_node]["y"]
    })

# Save mapping CSV for debugging
df_map = pd.DataFrame(records)
df_map.to_csv("TrafficLight_Node_Mapping.csv", index=False)
print("Saved mapping to TrafficLight_Node_Mapping.csv")
print(df_map.head())

# Plot graph with matched nodes highlighted
fig, ax = ox.plot_graph(
    G,
    node_size=0,
    edge_color="lightgrey",
    show=False,
    close=False
)

# Plot traffic light nodes in green
ax.scatter(
    df_map["node_lon"],
    df_map["node_lat"],
    c="green", s=30,
    label="Traffic Lights",
    zorder=5
)

plt.legend()
plt.show()
