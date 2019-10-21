#!/usr/bin/env python
import sys
import re
import os
import json
import pandas as pd
import geopandas
import numpy as np
from shapely.geometry import Point, Polygon


def create_field_polygons(cfg):
    # Creating a polygon for each field in config
    field_corners = {}
    for field in cfg['field_boundaries']:
        field_corners[field['name']] =  Polygon(
                            [(field['NW_corner']['latitude'],field['NW_corner']['longitude']),
                            (field['NE_corner']['latitude'], field['NE_corner']['longitude']),
                            (field['SE_corner']['latitude'], field['SE_corner']['longitude']),
                            (field['SW_corner']['latitude'], field['SW_corner']['longitude'])])

    # Geopandas library accounts for geometry of the polygons and land surfaces
    field_polygons = geopandas.GeoSeries(field_corners)
    return field_polygons


# Step 1: SPATIALLY FILTER: Data filtered based on the field coordinates
def filter_field_boundaries(cfg, filename, field_polygons):
    csv_directory = cfg['csv_directory']
    df = pd.read_csv(f'{csv_directory}/{filename}', encoding = "ISO-8859-1")

    # Storing all points located within the field polygons
    filtered_points = {}
    for field in cfg['field_boundaries']:
        # Adding points to the filtered_points object within lists identified by field name
        filtered_points[field['name']] = []

    for index, row in df.iterrows():
        try:
            # Iterating through rows of csv, creating a geopandas point using the df info
            point = Point(float(row['lat']), float(row['long']))

            # Iterating through each named field w/in the filtered_points object
            for field_name in filtered_points:
                # If the point is within the field, and does not contain zeros, add to that field
                if field_polygons[field_name].intersects(point) and not np.isnan(point.x) and not np.isnan(point.y):
                    # Append statement creates an object including the lat/long and weight for included points
                    filtered_points[field_name].append({'latitude': row['lat'], 'longitude':row['long'], 'weight':row['weight']})
        except:
            pass
    return filtered_points
    # filtered_points is now an object filled with lists of points within fields, and identified by field name

# Step 2: PROCESS WEIGHT: Steps through data using a spatial increment to calculate change in weight
def process_weight(cfg, filtered_points):
    processed_weight = {}  # object set up like filtered_points, to store lists identified by field names

    # Iterating through each field in the config
    for field in cfg['field_boundaries']:

        field_name = field['name']

        # Storing the calculated "yields," or changes in weight, as lists under each field name
        processed_weight[field_name] = []

        # Setting an initial point to calculate distance for the delta weight calculation
        try:
            initial_point = filtered_points[field_name][0]
        except:
            pass
        # Iterating through each point in the specific field the for loop above is at
        for i in range(0, len(filtered_points[field_name])):

            # Defining the initial point and intermediate point as geopandas GeoSeries to allow for accurate distance calc
            initial_point_series = geopandas.GeoSeries({'point': Point(float(initial_point['latitude']), float(initial_point['longitude']))})
            i_point_series = geopandas.GeoSeries({'point': Point(float(filtered_points[field_name][i]['latitude']), float(filtered_points[field_name][i]['longitude']))})
            # Calc distance between the intial point and intermediate point, allows for checking if distance interval is met yet
            distance = initial_point_series.distance(i_point_series)['point']

            # Once distance traveled exceeds the defined distance interval, then delta weight calculation happens
            if distance > cfg['distance_interval']:
                try:
                    # Center point between initial point and intermediate point set up for delta weight
                    midpoint = initial_point_series.union(i_point_series).centroid

                    # Removing anything that isn't a decimal point or a digit from recorded weights
                    i_weight = float(re.sub('[^A-Za-z0-9.]+', '', filtered_points[field_name][i]['weight']))
                    initial_weight = float(re.sub('[^A-Za-z0-9.]+', '', initial_point['weight']))

                    # Calculating change in weight between initial point and next "step" in space
                    delta_weight = i_weight - initial_weight

                    # Saving the delta weight to field's list w/in processed_weight object IF the change in weight is reasonable
                    # "Reasonable" currently defined as not extremely large or negative
                    # if delta < 300 and delta > -500:

                    # Append statement: appending objects containing lat/long/delta_weight to the field_name idenitified list
                    processed_weight[field_name].append({'lat': midpoint.x['point'], 'long': midpoint.y['point'], 'delta_weight': delta_weight}) # not dividing by distance

                    # Reset initial point for next run-through
                    initial_point = filtered_points[field_name][i]
                except:
                    pass
        # # Normalizing the delta weight by finding maximum value and dividing to create a percent/ratio
        # max_weight = max([point['delta_weight'] for point in processed_weight[field_name]])
        # for field_yield in processed_weight[field_name]:
        #     field_yield['delta_weight'] = field_yield['delta_weight']/max_weight

    return remove_noise(processed_weight)

def remove_noise(processed_weight):
    # iterating over the field names w/in the processed_weight object
    for field_name in processed_weight:
        # fetching the data (list of objects) for the field using the field name
        field = processed_weight[field_name]
        noise = set()
        for i in range(0, len(field)):
            if field[i]['delta_weight'] < 0 or field[i]['delta_weight'] > 250:
                noise.add(i)
                noise.add(i+1)
                noise.add(i-1)

        field_noise_removed = []
        for i in range(0, len(field)):
            if i not in list(noise):
                field_noise_removed.append(field[i])
        processed_weight[field_name] = field_noise_removed

    return processed_weight

# From Nik:
# smaller, symmetrical units for interpolation across the orchard instead of average by row
# Maybe means are calculated over an area of say 2-4 trees
# a typical orchard the trees are 9-10 feet apart for the early years then move to permanent spacing of 18-20 ft as they mature
# Should be  weigh cart data roughly every 3 sec, or every 9-12 ft if they drive 3-4 mph
# so maybe take a 400 ft square as the unit to include about 4 trees in 2 rows of 10 x 10 orchard to pool data.
# Or, maybe we pool data from a radius around the point?

def create_grid(cfg, field_polygons):
    xmin,ymin,xmax,ymax = field_polygons.total_bounds

    length = cfg['grid_interval']
    width = cfg['grid_interval']

    cols = list(np.arange(int(np.floor(xmin)), int(np.ceil(xmax)), width))
    rows = list(np.arange(int(np.floor(ymin)), int(np.ceil(ymax)), length))
    rows.reverse()

    polygons = []
    for x in cols:
        for y in rows:
            polygons.append( Polygon([(x,y), (x+width, y), (x+width, y-length), (x, y-length)]) )

    grid = geopandas.GeoDataFrame({'geometry':polygons})
    return grid


# Running all functions!
def main():
    with open("config.json", 'r') as json_data_file:
        cfg = json.load(json_data_file)
        field_polygons = create_field_polygons(cfg)
        # processed_weights = []
        # for filename in os.listdir(cfg['csv_directory']):
        #     if filename.endswith(".CSV"):
        #         filtered_points = filter_field_boundaries(cfg, filename, field_polygons)
        #         processed_weights.append(process_weight(cfg, filtered_points))
        grid = create_grid(cfg, field_polygons)

        # Output csv files with delta weight points for all fields
    #    for field in output:
            #Output_df = pd.DataFrame(data=output[field])
            #Output_df.to_csv(f'{field}.csv', index=False)


if __name__ == '__main__':
    sys.exit(main())
