import sys
import re
import os
import json
import pandas as pd
import geopandas
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon, LineString
import webcolors

def load_file(filepath):
    df = pd.read_csv(filepath, encoding = "ISO-8859-1")

    data = []
    for index, row in df.iterrows():
        try:
            point = Point(float(row['lat']), float(row['long']))
            # If the point does not contain zeros, add to list
            if not np.isnan(point.x) and not np.isnan(point.y):
                data.append({'lat': row['lat'], 'long':row['long'], 'weight':row['weight']})
        except:
            pass
    return data


def quantize_yield_intensity(data):
    intensities = []
    geometries = []
    if len(data) > 0:
        for i in range(0, len(data)-1):
            initial_point = data[i]
            final_point = data[i+1]
            initial_location = Point(float(initial_point['lat']), float(initial_point['long']))
            final_location = Point(float(final_point['lat']), float(final_point['long']))
            distance = geopandas.GeoSeries(initial_location).distance(geopandas.GeoSeries(final_location))[0]
            if distance > 0.0 and distance < 1e-4:
                try:
                    # Removing anything that isn't a decimal point or a digit from recorded weights
                    final_weight = float(re.sub('[^A-Za-z0-9.]+', '', final_point['weight']))
                    initial_weight = float(re.sub('[^A-Za-z0-9.]+', '', initial_point['weight']))
                    line = LineString([(initial_location.x, initial_location.y), (final_location.x, final_location.y)])
                    geometries.append(line)
                    intensity = (final_weight - initial_weight)/distance
                    intensities.append(intensity)
                except:
                    pass
    return intensities, geometries


intensities = []
geometries = []

data = load_file(f'/home/ian/spatial-crop-yield/yield-data/2018_merged/m.csv')
intensities, geometries = quantize_yield_intensity(data)

yield_df = pd.DataFrame(intensities, columns = ['intensity'])
yield_df = geopandas.GeoDataFrame(yield_df, geometry=geometries)

yield_df.to_file(f'yield_df.json', driver="GeoJSON")

with open(f'yield_df.json', 'r') as json_data_file:
    yield_json = json.load(json_data_file)
    for feature in yield_json['features']:
        line = feature['geometry']['coordinates']
        for point in line:
            long = point[0]
            lat = point[1]
            point[0] = lat
            point[1] = long

with open(f'yield_df_geojson.json', 'w') as outfile:
    json.dump(yield_json, outfile)
